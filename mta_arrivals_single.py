#!/usr/bin/env python3
"""
Single-run version of MTA arrivals for cron jobs
This version runs once and exits (no continuous monitoring)
"""

import requests
import json
from datetime import datetime, timezone
import os
from google.transit import gtfs_realtime_pb2
import sys

class MTAArrivals:
    def __init__(self):
        """Initialize MTA arrivals fetcher"""
        # MTA GTFS-RT feed URLs
        self.feeds = {
            'BDFM': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
            'NQRW': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw'
        }
        
        # Union Street station IDs
        self.union_stations = {
            'R20N': 'Union St (R/W) - Northbound',
            'R20S': 'Union St (R/W) - Southbound',
            'D24N': 'Union St-4th Ave (D/N/R/W) - Northbound',
            'D24S': 'Union St-4th Ave (D/N/R/W) - Southbound'
        }
    
    def fetch_feed_data(self, feed_url):
        """Fetch and parse GTFS-RT feed data"""        
        try:
            response = requests.get(feed_url, timeout=10)
            response.raise_for_status()
            
            # Parse the protobuf data
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            return feed
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return None
        except Exception as e:
            print(f"Error parsing feed data: {e}")
            return None
    
    def format_time(self, timestamp):
        """Convert Unix timestamp to readable time"""
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%I:%M %p')
        return "Unknown"
    
    def get_minutes_until(self, timestamp):
        """Calculate minutes until arrival"""
        if timestamp:
            now = datetime.now()
            arrival = datetime.fromtimestamp(timestamp)
            diff = (arrival - now).total_seconds() / 60
            return max(0, int(diff))
        return None
    
    def get_arrivals_for_station(self, feed, station_id):
        """Extract arrival times for a specific station"""
        arrivals = []
        
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                trip = entity.trip_update
                route_id = trip.trip.route_id
                
                for stop_update in trip.stop_time_update:
                    if stop_update.stop_id == station_id:
                        arrival_time = None
                        if stop_update.HasField('arrival'):
                            arrival_time = stop_update.arrival.time
                        elif stop_update.HasField('departure'):
                            arrival_time = stop_update.departure.time
                        
                        if arrival_time:
                            minutes_until = self.get_minutes_until(arrival_time)
                            arrivals.append({
                                'route': route_id,
                                'arrival_time': arrival_time,
                                'formatted_time': self.format_time(arrival_time),
                                'minutes_until': minutes_until
                            })
        
        # Sort by arrival time
        arrivals.sort(key=lambda x: x['arrival_time'])
        return arrivals
    
    def get_all_union_arrivals(self):
        """Get arrivals for all Union Street stations - single run"""
        print("🚇 MTA Live Arrivals - Union Street Stations")
        print("=" * 50)
        print(f"Last updated: {datetime.now().strftime('%I:%M:%S %p')}")
        print()
        
        all_arrivals = {}
        
        # Check BDFM feed for D line at Union St-4th Ave
        bdfm_feed = self.fetch_feed_data(self.feeds['BDFM'])
        if bdfm_feed:
            for station_id, station_name in self.union_stations.items():
                if 'D24' in station_id:  # Union St-4th Ave station
                    arrivals = self.get_arrivals_for_station(bdfm_feed, station_id)
                    if arrivals:
                        all_arrivals[station_name] = arrivals
        
        # Check NQRW feed for N, R, W lines
        nqrw_feed = self.fetch_feed_data(self.feeds['NQRW'])
        if nqrw_feed:
            for station_id, station_name in self.union_stations.items():
                arrivals = self.get_arrivals_for_station(nqrw_feed, station_id)
                if arrivals:
                    if station_name in all_arrivals:
                        all_arrivals[station_name].extend(arrivals)
                    else:
                        all_arrivals[station_name] = arrivals
        
        # Display results
        print("\n" + "=" * 50)
        if not all_arrivals:
            print("No arrival data found for Union Street stations.")
            return
        
        for station_name, arrivals in all_arrivals.items():
            print(f"\n📍 {station_name}")
            print("-" * 40)
            
            if not arrivals:
                print("No upcoming arrivals")
                continue
            
            # Sort all arrivals by time and take next 3 for cron version
            arrivals.sort(key=lambda x: x['arrival_time'])
            next_arrivals = arrivals[:3]
            
            for arrival in next_arrivals:
                route = arrival['route']
                time_str = arrival['formatted_time']
                minutes = arrival['minutes_until']
                
                if minutes == 0:
                    status = "Now"
                elif minutes == 1:
                    status = "1 min"
                else:
                    status = f"{minutes} mins"
                
                print(f"  🚊 {route} train: {time_str} ({status})")


def main():
    """Main function - single run only"""
    mta = MTAArrivals()
    mta.get_all_union_arrivals()


if __name__ == "__main__":
    main()