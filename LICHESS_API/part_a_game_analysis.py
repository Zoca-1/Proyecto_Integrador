"""
part_a_game_analysis.py

Lichess API - Game Analysis
============================
Downloads a user's game history from the Lichess API, processes it into a
pandas DataFrame, computes descriptive statistics, renders a dashboard of
charts, and exports both the raw dataset and the statistics to CSV.

Usage:
    python part_a_game_analysis.py --username DrNykterstein --max-games 200
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv

LICHESS_API_BASE = "https://lichess.org"
GAMES_EXPORT_ENDPOINT = f"{LICHESS_API_BASE}/api/games/user/{{username}}"

# Lichess silently returns a fake 404 to requests carrying the default
# python-requests/curl User-Agent (anti-bot heuristic). A descriptive UA, as
# recommended by the Lichess API docs, avoids that and surfaces the real
# response (e.g. a genuine 429 rate limit).
USER_AGENT = "lichess-data-analysis-tool/1.0 (+part_a_game_analysis.py)"

DEFAULT_USERNAME = "DrNykterstein"
DEFAULT_MAX_GAMES = 200

MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 1.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("lichess.part_a")


@dataclass
class ApiConfig:
    """Holds the API token and derives the request headers from it."""

    token: Optional[str]

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Accept": "application/x-ndjson", "User-Agent": USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers


def load_config() -> ApiConfig:
    """Load the Lichess API token from the .env file, if present."""
    load_dotenv()
    token = os.getenv("LICHESS_API_TOKEN")
    if not token:
        logger.warning(
            "LICHESS_API_TOKEN not set. Continuing without authentication "
            "(only public data is accessible and rate limits are lower)."
        )
    return ApiConfig(token=token)


def fetch_games(username: str, max_games: int, config: ApiConfig) -> list[dict[str, Any]]:
    """Stream up to `max_games` games for `username` from the Lichess API.

    Handles HTTP 429 (rate limiting) with exponential backoff. A failure on
    this single request never raises past this function; it logs and returns
    whatever games were collected so far.
    """
    params = {
        "max": max_games,
        "moves": "false",
        "pgnInJson": "false",
        "opening": "false",
    }
    url = GAMES_EXPORT_ENDPOINT.format(username=username)

    games: list[dict[str, Any]] = []
    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(
                url, headers=config.headers, params=params, stream=True, timeout=30
            ) as response:
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff))
                    logger.warning(
                        "Rate limited (429). Retrying in %.1fs (attempt %d/%d).",
                        retry_after, attempt, MAX_RETRIES,
                    )
                    time.sleep(retry_after)
                    backoff *= 2
                    continue

                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        games.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        logger.error("Skipping malformed game record: %s", exc)

                logger.info("Fetched %d games for user '%s'.", len(games), username)
                return games

        except requests.exceptions.RequestException as exc:
            logger.error("Request failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            time.sleep(backoff)
            backoff *= 2

    logger.error(
        "Giving up after %d attempts. Returning %d games collected so far.",
        MAX_RETRIES, len(games),
    )
    return games


def _extract_result(game: dict[str, Any], color: str) -> str:
    """Map a raw game record to 'Win' / 'Loss' / 'Draw' from `color`'s view."""
    status = game.get("status")
    winner = game.get("winner")
    if status in ("draw", "stalemate") or winner is None:
        return "Draw"
    return "Win" if winner == color else "Loss"


def games_to_dataframe(games: list[dict[str, Any]], username: str) -> pd.DataFrame:
    """Flatten raw Lichess game JSON objects into a tabular DataFrame."""
    username_lower = username.lower()
    records: list[dict[str, Any]] = []

    for game in games:
        try:
            players = game.get("players", {})
            white = players.get("white", {})
            black = players.get("black", {})

            white_name = (white.get("user") or {}).get("name", "").lower()
            if white_name == username_lower:
                color, player, opponent = "white", white, black
            else:
                color, player, opponent = "black", black, white

            records.append({
                "game_id": game.get("id"),
                "created_at": pd.to_datetime(game.get("createdAt"), unit="ms", errors="coerce"),
                "color": color.capitalize(),
                "result": _extract_result(game, color),
                "player_rating": player.get("rating"),
                "opponent_rating": opponent.get("rating"),
                "opponent_name": (opponent.get("user") or {}).get("name", "Anonymous"),
                "variant": game.get("variant", "standard"),
                "speed": game.get("speed", "unknown"),
                "rated": game.get("rated", False),
                "status": game.get("status"),
            })
        except Exception as exc:
            logger.error("Skipping malformed game %s: %s", game.get("id", "?"), exc)

    df = pd.DataFrame.from_records(records)
    if not df.empty:
        df["rating_diff"] = df["player_rating"] - df["opponent_rating"]
    return df


def compute_statistics(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute descriptive statistics grouped by result, rating, color and speed."""
    if df.empty:
        logger.warning("Empty DataFrame: no statistics to compute.")
        return {}

    stats: dict[str, pd.DataFrame] = {}
    stats["by_result"] = df.groupby("result").size().rename("count").reset_index()
    stats["rating_summary"] = df[["player_rating", "opponent_rating"]].describe()
    stats["by_color"] = df.groupby(["color", "result"]).size().unstack(fill_value=0)
    stats["by_speed"] = df.groupby(["speed", "result"]).size().unstack(fill_value=0)
    stats["win_rate_by_speed"] = (
        df.assign(is_win=(df["result"] == "Win").astype(int))
        .groupby("speed")["is_win"]
        .mean()
        .rename("win_rate")
        .reset_index()
    )
    return stats


def plot_dashboard(df: pd.DataFrame, stats: dict[str, pd.DataFrame], output_path: str) -> None:
    """Render a 2x2 dashboard of charts and save it to `output_path`."""
    if df.empty:
        logger.warning("Nothing to plot: DataFrame is empty.")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Lichess Game Analysis Dashboard", fontsize=16, fontweight="bold")

    # 1. Result distribution (pie chart)
    result_counts = df["result"].value_counts()
    axes[0, 0].pie(result_counts, labels=result_counts.index, autopct="%1.1f%%", startangle=90)
    axes[0, 0].set_title("Result Distribution")

    # 2. Rating distribution (histogram)
    axes[0, 1].hist(df["player_rating"].dropna(), bins=20, color="steelblue", edgecolor="black")
    axes[0, 1].set_title("Player Rating Distribution")
    axes[0, 1].set_xlabel("Rating")
    axes[0, 1].set_ylabel("Frequency")

    # 3. Performance by color (stacked bar)
    by_color = stats.get("by_color", pd.DataFrame())
    if not by_color.empty:
        by_color.plot(kind="bar", stacked=True, ax=axes[1, 0])
        axes[1, 0].set_title("Results by Color")
        axes[1, 0].set_xlabel("Color")
        axes[1, 0].set_ylabel("Games")
        axes[1, 0].legend(title="Result")
        axes[1, 0].tick_params(axis="x", rotation=0)

    # 4. Win rate by game mode
    win_rate = stats.get("win_rate_by_speed", pd.DataFrame())
    if not win_rate.empty:
        axes[1, 1].bar(win_rate["speed"], win_rate["win_rate"], color="seagreen")
        axes[1, 1].set_title("Win Rate by Game Mode")
        axes[1, 1].set_xlabel("Mode")
        axes[1, 1].set_ylabel("Win Rate")
        axes[1, 1].set_ylim(0, 1)

    plt.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Dashboard saved to '%s'.", output_path)


def export_data(
    df: pd.DataFrame,
    stats: dict[str, pd.DataFrame],
    games_csv: str,
    stats_csv: str,
) -> None:
    """Persist the processed DataFrame and flattened statistics to CSV."""
    df.to_csv(games_csv, index=False)
    logger.info("Games data exported to '%s'.", games_csv)

    if not stats:
        logger.warning("No statistics to export.")
        return

    summary_rows: list[dict[str, Any]] = []
    for _, row in stats["by_result"].iterrows():
        summary_rows.append({"metric": "result_count", "key": row["result"], "value": row["count"]})
    for _, row in stats["win_rate_by_speed"].iterrows():
        summary_rows.append({"metric": "win_rate_by_speed", "key": row["speed"], "value": row["win_rate"]})

    pd.DataFrame(summary_rows).to_csv(stats_csv, index=False)
    logger.info("Statistics exported to '%s'.", stats_csv)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lichess game analysis")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Lichess username to analyze")
    parser.add_argument("--max-games", type=int, default=DEFAULT_MAX_GAMES, help="Maximum number of games to fetch")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()

    logger.info("Fetching up to %d games for '%s'...", args.max_games, args.username)
    games = fetch_games(args.username, args.max_games, config)

    df = games_to_dataframe(games, args.username)
    stats = compute_statistics(df)

    plot_dashboard(df, stats, "lichess_analysis.png")
    export_data(df, stats, "games_data.csv", "game_statistics.csv")


if __name__ == "__main__":
    main()
