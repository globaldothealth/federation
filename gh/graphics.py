"""
Functions for creating data visualizations
"""

from datetime import date
import logging

import matplotlib.pyplot as plt

from constants import RT_PARAMS


def create_plot(data: list, location: str) -> str:
    """
    Create a plot for R(t) estimation

    Args:
        data (list): R(t) estimation data
        location (str): Name of the location

    Returns:
        str: File name for generated plot
    """
    file_name = f"{date.today()}_{location}.png"
    logging.debug(f"Creating plot: {file_name}")
    plt.style.use("seaborn-white")
    fig, ax = plt.subplots(1, 1, figsize=(12, 4))

    confidence = 100 * (RT_PARAMS.get("q_upper", 0) - RT_PARAMS.get("q_lower", 0))

    means = [d.get("rMean") for d in data]
    dates = [d.get("date") for d in data]
    lowers = [d.get("qLower") for d in data]
    uppers = [d.get("qUpper") for d in data]

    plt.plot(means, color="red")
    ax.fill_between(dates, lowers, uppers, color="red", alpha=0.2)
    ax.set_xlabel("date")
    ax.set_ylabel(f"R(t) with {confidence}%-CI")
    ax.set_ylim([0, 3])
    ax.axhline(y=1)
    ax.set_title(
        f"Estimate of time-varying effective reproduction number for {location}"
    )
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(file_name)
    return file_name
