from datetime import datetime
import logging

from epyestim import bagging_r
import numpy as np
import pandas as pd


def bag(cases, quantiles, gt_dist, delay_dist):
	gt_distribution = np.array(gt_dist)
	delay_distribution = np.array(delay_dist)

	return bagging_r(
		confirmed_cases=cases,
		gt_distribution=gt_distribution,
		delay_distribution=delay_distribution,
		a_prior=1,
		b_prior=3,
		n_samples=100,
		smoothing_window=14,
		r_window_size=1,
		quantiles=quantiles
	)


def estimate_rt(partner_cases, date_range, quantiles, gt_dist, delay_dist):
	logging.debug("Estimating R(t)")
	start_date = datetime.strptime(date_range[0], "%m-%d-%Y")
	end_date = datetime.strptime(date_range[1], "%m-%d-%Y")
	logging.debug(f"Date range: {date_range[0]} to {date_range[1]}")
	q_lower = quantiles[0]
	q_upper = quantiles[1]
	logging.debug(f"Lower quantile: {q_lower}, upper quantile: {q_upper}")
	logging.debug(f"G(t) distribution: {gt_dist}")
	logging.debug(f"Delay distribution: {delay_dist}")
	counts_by_day = {}
	for case in partner_cases:
		date = case.get("date_confirmation")
		dt_date = datetime.strptime(date, "%m-%d-%Y")
		if dt_date < start_date or dt_date > end_date:
			continue
		if counts_by_day.get(dt_date):
			counts_by_day[dt_date] += 1
		else:
			counts_by_day[dt_date] = 1
	running_count = 0
	for day, count in counts_by_day.items():
		running_count += count
		counts_by_day[day] = running_count
	cases = pd.Series(counts_by_day, index=counts_by_day.keys())
	results = bag(cases.sort_index(), quantiles, gt_dist, delay_dist)
	results.reset_index(inplace=True)
	results.rename(columns={"index": "date", f"Q{q_lower}": "q_lower", f"Q{q_upper}": "q_upper"}, inplace=True)

	return results.to_dict(orient="records")
