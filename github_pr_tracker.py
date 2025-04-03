"""
GitHub PR Tracker

This script fetches closed pull requests from a GitHub repository within a specified time frame,
identifies users who closed them, and produces a day-by-day cumulative count of PRs closed by each user.

Usage:
    python github_pr_tracker.py --repo owner/repo --start YYYY-MM-DD --end YYYY-MM-DD [--output format] [--token TOKEN]

Arguments:
    --repo: GitHub repository in owner/repo format
    --start: Start date in YYYY-MM-DD format
    --end: End date in YYYY-MM-DD format
    --output: Output format (json or csv, default: json)
    --token: GitHub personal access token (optional, uses environment variable GITHUB_TOKEN if not provided)
    --visualize: Generate visualization (optional, default: False)
"""

import argparse
import csv
import datetime
import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Any

import requests
from dateutil import parser as date_parser

try:
    import matplotlib.pyplot as plt
    import pandas as pd
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False


class GitHubPRTracker:
    """Class to track GitHub PR closures by user within a specified timeframe."""

    def __init__(self, repo: str, token: str = None):
        """
        Initialize the GitHub PR tracker.

        Args:
            repo: GitHub repository in owner/repo format
            token: GitHub personal access token
        """
        self.repo = repo
        self.token = token or os.environ.get('GITHUB_TOKEN')
        if not self.token:
            print("Warning: No GitHub token provided. API rate limits may apply.")
        
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'

    def fetch_closed_prs(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Fetch all closed PRs within the specified time frame.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of PR data dictionaries
        """
        start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        end_dt = end_dt + datetime.timedelta(days=1)
        
        start_date_iso = start_dt.isoformat()
        end_date_iso = end_dt.isoformat()
        
        print(f"Fetching closed PRs between {start_date} and {end_date}...")
        
        params = {
            'state': 'closed',
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 100,
        }
        
        all_prs = []
        page = 1
        
        while True:
            params['page'] = page
            url = f"{self.base_url}/pulls"
            
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code != 200:
                print(f"Error fetching PRs: {response.status_code}")
                print(response.text)
                sys.exit(1)
            
            prs = response.json()
            if not prs:
                break
            
            filtered_prs = []
            for pr in prs:
                closed_at = pr.get('closed_at')
                if not closed_at:
                    continue
                
                closed_dt = date_parser.parse(closed_at)
                if start_dt <= closed_dt < end_dt:
                    filtered_prs.append(pr)
                elif closed_dt < start_dt:
                    break
            
            all_prs.extend(filtered_prs)
            
            if len(prs) < 100 or not filtered_prs:
                break
            
            page += 1
            print(f"Fetched page {page-1}, found {len(filtered_prs)} PRs in this page...")
        
        print(f"Found {len(all_prs)} closed PRs within the specified time frame.")
        return all_prs

    def identify_closers(self, prs: List[Dict]) -> List[Dict]:
        """
        Identify users who closed each PR.

        Args:
            prs: List of PR data dictionaries

        Returns:
            List of dictionaries with PR data and closer information
        """
        print("Identifying users who closed PRs...")
        
        pr_data = []
        for pr in prs:
            pr_number = pr['number']
            closed_at = pr['closed_at']
            
            url = f"{self.base_url}/pulls/{pr_number}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"Error fetching PR details: {response.status_code}")
                continue
            
            pr_detail = response.json()
            
            closer = None
            merged = pr_detail.get('merged')
            
            if merged:
                closer = pr_detail.get('merged_by', {}).get('login')
            else:
                events_url = f"{self.base_url}/issues/{pr_number}/timeline"
                events_headers = self.headers.copy()
                events_headers['Accept'] = 'application/vnd.github.mockingbird-preview+json'
                
                events_response = requests.get(events_url, headers=events_headers)
                if events_response.status_code == 200:
                    events = events_response.json()
                    for event in events:
                        if event.get('event') == 'closed':
                            closer = event.get('actor', {}).get('login')
                            break
            
            if not closer:
                closer = pr.get('user', {}).get('login')
            
            pr_data.append({
                'pr_number': pr_number,
                'closed_at': closed_at,
                'closer': closer,
                'title': pr.get('title'),
                'url': pr.get('html_url')
            })
        
        return pr_data

    def calculate_cumulative_counts(self, pr_data: List[Dict]) -> List[Dict]:
        """
        Calculate day-by-day cumulative counts of PRs closed by each user.

        Args:
            pr_data: List of dictionaries with PR data and closer information

        Returns:
            List of dictionaries with date, username, and cumulative count
        """
        print("Calculating day-by-day cumulative counts...")
        
        pr_data.sort(key=lambda x: x['closed_at'])
        
        daily_counts = defaultdict(lambda: defaultdict(int))
        
        cumulative_counts = []
        
        for pr in pr_data:
            closer = pr['closer']
            closed_date = date_parser.parse(pr['closed_at']).date().isoformat()
            
            daily_counts[closed_date][closer] += 1
        
        user_totals = defaultdict(int)
        
        all_dates = sorted(daily_counts.keys())
        all_users = set()
        for date_counts in daily_counts.values():
            all_users.update(date_counts.keys())
        
        for date in all_dates:
            for user in all_users:
                user_totals[user] += daily_counts[date].get(user, 0)
                cumulative_counts.append({
                    'date': date,
                    'username': user,
                    'cumulative_count': user_totals[user]
                })
        
        return cumulative_counts

    def save_results(self, results: List[Dict], output_format: str, output_file: str = None) -> None:
        """
        Save results in the specified format.

        Args:
            results: List of dictionaries with date, username, and cumulative count
            output_format: Output format (json or csv)
            output_file: Output file name (optional)
        """
        if not output_file:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"pr_counts_{timestamp}.{output_format}"
        
        print(f"Saving results to {output_file}...")
        
        if output_format == 'json':
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
        elif output_format == 'csv':
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'username', 'cumulative_count'])
                writer.writeheader()
                writer.writerows(results)
        
        print(f"Results saved to {output_file}")
        return output_file

    def visualize_results(self, results: List[Dict], output_file: str = None) -> None:
        """
        Create a visualization of PR closures over time by user.

        Args:
            results: List of dictionaries with date, username, and cumulative count
            output_file: Output file name for the visualization (optional)
        """
        if not VISUALIZATION_AVAILABLE:
            print("Visualization libraries (matplotlib, pandas) not available. Skipping visualization.")
            return
        
        print("Creating visualization...")
        
        df = pd.DataFrame(results)
        
        pivot_df = df.pivot(index='date', columns='username', values='cumulative_count')
        
        plt.figure(figsize=(12, 8))
        pivot_df.plot(marker='o', linestyle='-', ax=plt.gca())
        
        plt.title('Cumulative PR Closures by User')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Count')
        plt.grid(True)
        plt.legend(title='Username')
        
        if not output_file:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"pr_visualization_{timestamp}.png"
        
        plt.savefig(output_file)
        print(f"Visualization saved to {output_file}")
        return output_file


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Track GitHub PR closures by user within a specified timeframe.')
    parser.add_argument('--repo', required=True, help='GitHub repository in owner/repo format')
    parser.add_argument('--start', required=True, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end', required=True, help='End date in YYYY-MM-DD format')
    parser.add_argument('--output', choices=['json', 'csv'], default='json', help='Output format (json or csv)')
    parser.add_argument('--token', help='GitHub personal access token')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization')
    
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_args()
    
    try:
        datetime.datetime.strptime(args.start, '%Y-%m-%d')
        datetime.datetime.strptime(args.end, '%Y-%m-%d')
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        sys.exit(1)
    
    tracker = GitHubPRTracker(args.repo, args.token)
    
    prs = tracker.fetch_closed_prs(args.start, args.end)
    
    pr_data = tracker.identify_closers(prs)
    
    results = tracker.calculate_cumulative_counts(pr_data)
    
    output_file = tracker.save_results(results, args.output)
    
    if args.visualize:
        if VISUALIZATION_AVAILABLE:
            tracker.visualize_results(results)
        else:
            print("Visualization libraries not available. Install matplotlib and pandas to enable visualization.")
    
    print("Done!")


if __name__ == '__main__':
    main()
