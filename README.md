# GitHub PR Tracker

A Python tool to track GitHub pull request closures by user within a specified timeframe.

## Features

- Fetch closed pull requests within a specified time frame
- Identify users who closed each PR (author or merger)
- Calculate day-by-day cumulative counts of PRs closed by each user
- Output results in JSON or CSV format
- Optional visualization of PR closures over time

## Installation

```bash
# Clone the repository
git clone https://github.com/jianhuanggo/github_pr_count.git
cd github_pr_count

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python github_pr_tracker.py --repo owner/repo --start YYYY-MM-DD --end YYYY-MM-DD [--output format] [--token TOKEN] [--visualize]
```

### Arguments

- `--repo`: GitHub repository in owner/repo format
- `--start`: Start date in YYYY-MM-DD format
- `--end`: End date in YYYY-MM-DD format
- `--output`: Output format (json or csv, default: json)
- `--token`: GitHub personal access token (optional, uses environment variable GITHUB_TOKEN if not provided)
- `--visualize`: Generate visualization (optional)

### Example

```bash
# Track PRs closed in the last month for a repository
python github_pr_tracker.py --repo octocat/Hello-World --start 2023-01-01 --end 2023-01-31 --output csv --visualize
```

## Output

The tool produces a file containing the day-by-day cumulative count of PRs closed by each user:

### JSON Format
```json
[
  {
    "date": "2023-01-01",
    "username": "octocat",
    "cumulative_count": 1
  },
  {
    "date": "2023-01-01",
    "username": "other-user",
    "cumulative_count": 2
  },
  ...
]
```

### CSV Format
```
date,username,cumulative_count
2023-01-01,octocat,1
2023-01-01,other-user,2
...
```

If visualization is enabled, the tool will also generate a line chart showing the cumulative PR closures over time by user.

## Authentication

For higher API rate limits, provide a GitHub personal access token:

```bash
# Using command line argument
python github_pr_tracker.py --repo owner/repo --start YYYY-MM-DD --end YYYY-MM-DD --token YOUR_TOKEN

# Using environment variable
export GITHUB_TOKEN=YOUR_TOKEN
python github_pr_tracker.py --repo owner/repo --start YYYY-MM-DD --end YYYY-MM-DD
```

## License

MIT
