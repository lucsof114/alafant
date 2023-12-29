
def find_continuous_ranges(inseries, where):
    series = where(inseries.reset_index(drop=True))
    # series = series.loc[where(series)]
    if series.empty:
        return []
    series_idx = series.index.to_series()
    end_diffs = series_idx - series_idx.shift(-1)
    start_diffs = series_idx - series_idx.shift(1)
    return [[start, end] for start, end in zip(series_idx[start_diffs != 1], series_idx[end_diffs != -1])]
