#!/usr/bin/env python3
"""
====================================================================================
MTA SUBWAY LIVE ARRIVALS DISPLAY SYSTEM
====================================================================================

WHAT THIS PROGRAM DOES:
This program shows real-time subway train arrival information for the Nostrand Ave-Fulton St 
station in Brooklyn, NY. It displays when the next A and C trains are arriving, both on your 
computer screen and on a physical e-paper display (like a digital sign).

HOW IT WORKS:
1. Connects to MTA's computer servers over the internet
2. Downloads real-time train arrival data every 30 seconds
3. Filters the data to show only trains arriving at Nostrand Ave-Fulton St
4. Displays the information in two places:
   - Your computer's terminal window (text display)
   - An e-paper screen (like a small digital sign you can mount on a wall)

WHAT IT SHOWS:
- Which train line is arriving (A or C)
- What time it will arrive (like 3:45 PM)
- How many minutes away it is (like "5 mins")
- Separate columns for northbound and southbound trains

THE E-PAPER SCREEN:
The e-paper display is a special kind of screen that looks like paper and only uses power when
updating. It's perfect for showing information that changes occasionally. This program formats
the train data to fit nicely on the small screen and updates it every 30 seconds.

====================================================================================
"""

"""
this section imports "Libraries". These are pre-written code shared freely by other developers.
They are usually very specific. For example the "datetime" library helps with date and time functions.
Each one of these libraries is filled with "functions" that you can use in your own code to make your life easier.
"""
import requests
import json
from datetime import datetime, timezone
import os
from google.transit import gtfs_realtime_pb2
import sys
import logging
from PIL import Image, ImageDraw, ImageFont
import traceback

"""
E-paper display imports: These libraries are specific to that screen, and aren't available from the global Python "imports" so they
are stored in a local "lib" folder.

These two lines are importing the libraries from the computer itself and saving them as the names "picdir" and "libdir" for later use.
"""
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pic')
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')

"""
Quick note on the structure of the "language" itself:

lets translate the line "os.path.exists(libdir)" into human speak. Its saying to take the library called "os" and
use the function inside that libary called "path". Then check if a certain "path" exists on the computer. The path is the one
we stored under the name "libdir" earlier. 
"""
if os.path.exists(libdir):
    sys.path.append(libdir)

try:
    from waveshare_epd import epd2in9
    EPD_AVAILABLE = True
except ImportError as e:
    EPD_AVAILABLE = False

"""
All the work above this point is just setting up our environment. It imports all the pre-written code that we want to use,
and makes sure it all loads properly. After this point is where we start writing our own code to do what we want. The first thing
we are doing is creating a "class" called MTAArrivals. A class is a way to group together a bunch of functions and data that are related to each other
so that we can use it over and over again if we want to.
"""
class MTAArrivals:
    def __init__(self, use_epd=True):
        """Initialize MTA arrivals. This creates the class object and sets up initial variables."""
        # MTA GTFS-RT feed URLs: this is the specific address of the computer owned by MTA that spits out the data we want.
        # Think of this like a website address, but for computers to talk to each other instead of humans browsing
        self.feeds = {
            'ACE': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace'
        }
        """
        Nostrand Ave-Fulton St station IDs: these are the specific identifiers for the station platforms we want to track.
        the identifier A32N and A32S are defined by MTA. So if we want to track a different station we need to check with MTA
        to see what the station we want is called in their system.
        """

        self.nostrand_stations = {
            'A32N': 'Nostrand Ave-Fulton St (A/C) - Northbound',
            'A32S': 'Nostrand Ave-Fulton St (A/C) - Southbound'
        }
        
        # Create a persistent connection to MTA's servers so we don't have to reconnect every time
        # This is like keeping a phone line open instead of hanging up and redialing every time
        self.session = requests.Session()
        
        # Set up the e-paper display (the physical screen that shows the train times)
        self.use_epd = use_epd and EPD_AVAILABLE
        self.epd = None  # This will store our connection to the screen
        self.font_large = None  # These will store different font sizes for text on the screen
        self.font_medium = None
        self.font_small = None
        self.update_count = 0  # Count how many times we've updated the screen (to know when to do a full refresh)
        
        # If we're using the e-paper display, set it up
        if self.use_epd:
            try:
                # Set up logging (this helps us see what's happening behind the scenes)
                logging.basicConfig(level=logging.INFO)
                # Connect to the e-paper display hardware
                self.epd = epd2in9.EPD()
                # Do a full screen refresh first to clear everything and start fresh
                self.epd.init(self.epd.lut_full_update)
                self.epd.Clear(0xFF)  # 0xFF means "white" - clear the screen to white
                # Switch to partial update mode (faster updates that only change what's different)
                # This is like only erasing and redrawing the parts of the screen that changed
                self.epd.init(self.epd.lut_partial_update)
                
                # Load the fonts (typefaces) we'll use to write text on the screen
                # Find where the font file is stored on the computer
                font_path = os.path.join(picdir, 'Font.ttc')
                
                # Check if the font file exists where we expect it
                if os.path.exists(font_path):
                    # Load three different sizes of the same font (24, 18, and 14 pixels tall)
                    self.font_large = ImageFont.truetype(font_path, 24)
                    self.font_medium = ImageFont.truetype(font_path, 18)
                    self.font_small = ImageFont.truetype(font_path, 14)
                else:
                    # If we can't find our custom font, use the computer's basic default font instead
                    self.font_large = ImageFont.load_default()
                    self.font_medium = ImageFont.load_default()
                    self.font_small = ImageFont.load_default()
                
            except Exception as e:
                # If anything goes wrong setting up the display, turn it off so the program can still run
                self.use_epd = False
    
    def fetch_feed_data(self, feed_url):
        """This function contacts MTA's servers and downloads the latest train arrival data"""
        try:
            # Request the data from MTA (like asking for information)
            # The timeout=10 means "give up if it takes more than 10 seconds"
            response = self.session.get(feed_url, timeout=10)
            # Check if the request was successful (if MTA's servers responded properly)
            response.raise_for_status()
            
            # Convert the data we received into a format we can work with
            # MTA sends data in a special format called "protobuf" - this converts it to something we can read
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            # Close the connection to MTA's server now that we have the data
            # This is like hanging up the phone after you got the information you needed
            response.close()
            
            # Send back the data we downloaded
            return feed
            
        except requests.exceptions.RequestException as e:
            # If something went wrong contacting MTA's servers, print an error message
            print(f"Error fetching data: {e}")
            return None
        except Exception as e:
            # If something went wrong converting the data, print an error message
            print(f"Error parsing feed data: {e}")
            return None
    
    def format_time(self, timestamp):
        """Convert a computer timestamp into a human-readable time like '3:45 PM'"""
        # Computers store time as a number (seconds since January 1, 1970)
        # This function converts that number into something humans can read
        if timestamp:
            # Convert the number to a date/time object
            dt = datetime.fromtimestamp(timestamp)
            # Format it as "Hour:Minutes AM/PM" (like 3:45 PM)
            return dt.strftime('%I:%M %p')
        return "Unknown"
    
    def get_minutes_until(self, timestamp):
        """Calculate how many minutes from now until the train arrives"""
        # This is like looking at a clock and figuring out "the train comes in 5 minutes"
        if timestamp:
            now = datetime.now()  # Get the current time
            arrival = datetime.fromtimestamp(timestamp)  # Convert train's arrival time to readable format
            diff = (arrival - now).total_seconds() / 60  # Calculate difference in minutes
            return max(0, int(diff))  # Return the number of minutes (never less than 0)
        return None
    
    def get_arrivals_for_station(self, feed, station_id):
        """Look through all the train data and find the arrivals for our specific station"""
        # MTA sends data for ALL trains - we need to filter it to only our station
        arrivals = []  # Create an empty list to store the arrivals we find
        
        # Loop through each train update in the data feed
        # Think of this like going through a long list of trains one by one
        for entity in feed.entity:
            # Check if this entry has trip update information (not all entries do)
            if entity.HasField('trip_update'):
                trip = entity.trip_update  # Get the trip information
                route_id = trip.trip.route_id  # Get which line this train is on (A, C, etc.)
                
                # Only track A and C lines - skip E trains and anything else
                if route_id not in ('A', 'C'):
                    continue
                
                # Each trip has multiple stops - loop through them to find our station
                for stop_update in trip.stop_time_update:
                    # Check if this stop is the station we're looking for
                    if stop_update.stop_id == station_id:
                        arrival_time = None
                        # Try to get the arrival time (when the train arrives)
                        if stop_update.HasField('arrival'):
                            arrival_time = stop_update.arrival.time
                        # If no arrival time, use departure time (when it leaves) as backup
                        elif stop_update.HasField('departure'):
                            arrival_time = stop_update.departure.time
                        
                        # If we found a time, save all the important information about this train
                        if arrival_time:
                            minutes_until = self.get_minutes_until(arrival_time)
                            # Create a package of information about this train arrival
                            arrivals.append({
                                'route': route_id,  # Which train line (A, C, etc.)
                                'arrival_time': arrival_time,  # When it arrives (computer format)
                                'formatted_time': self.format_time(arrival_time),  # When it arrives (human format)
                                'minutes_until': minutes_until  # How many minutes from now
                            })
        
        # Sort all the arrivals we found by time, so the soonest train is first
        arrivals.sort(key=lambda x: x['arrival_time'])
        return arrivals  # Send back the list of arrivals for this station
    
    def display_on_epd(self, all_arrivals):
        """Take all the train arrival information and show it on the e-paper screen"""
        # This is like taking all the train times and drawing them on a piece of paper
        # If the screen isn't set up or available, don't try to display anything
        if not self.use_epd or not self.epd:
            return
        
        # Keep track of how many times we've updated the screen
        self.update_count += 1
        
        # Every 120 updates, do a full screen refresh to prevent "ghost" images
        # E-paper screens can sometimes leave faint traces of old text - a full refresh clears this
        try:
            if self.update_count % 120 == 0:  # % means "remainder" - this is true every 120 times
                if self.update_count > 120:  # Skip the very first time (we already did a full refresh)
                    self.epd.init(self.epd.lut_full_update)
            # For regular updates, keep using partial update mode (faster)
        except Exception as e:
            print(f"⚠️  Error initializing EPD for update: {e}")
            # Even if there's an error, keep going and try to update the display anyway
            
        try:
            # Create a blank image to draw on (296 pixels wide by 128 pixels tall for a 2.9" screen)
            # The '1' means it's black and white (not color), 255 means start with white
            image = Image.new('1', (self.epd.height, self.epd.width), 255)  # 255 = white
            # Get a "pen" to draw on the image
            draw = ImageDraw.Draw(image)
            
            # Write the title at the top of the screen
            current_time = datetime.now().strftime('%H:%M:%S')  # Get current time in HH:MM:SS format
            draw.text((5, 5), 'MTA Arrivals', font=self.font_medium, fill=0)  # (5,5) is 5 pixels from left, 5 from top
            draw.text((200, 5), current_time, font=self.font_small, fill=0)  # Show time on right side
            
            # Write the station name below the title
            draw.text((5, 30), 'Nostrand Ave-Fulton St', font=self.font_small, fill=0)
            
            # Draw a horizontal line to separate the header from the train times
            draw.line((5, 50, 290, 50), fill=0)  # Line from (5,50) to (290,50)
            
            # Set up where to start writing train times (y_pos = vertical position)
            y_pos = 55
            line_height = 18  # How many pixels between each line of text
            
            # If there are no trains to display, show a message explaining why
            if not all_arrivals:
                draw.text((5, y_pos), 'No arrival data available', font=self.font_small, fill=0)
                draw.text((5, y_pos + 20), 'Trains may not be running', font=self.font_small, fill=0)
                draw.text((5, y_pos + 35), 'or service is disrupted', font=self.font_small, fill=0)
            else:
                # If we have train data, separate it into northbound and southbound trains
                nb_arrivals = []  # Trains going north
                sb_arrivals = []  # Trains going south
                
                # Go through all the arrivals and sort them by direction
                for station_name, arrivals in all_arrivals.items():
                    if "Northbound" in station_name:
                        nb_arrivals = arrivals
                    else:
                        sb_arrivals = arrivals
                
                # Sort each direction's trains by time (soonest first)
                nb_arrivals.sort(key=lambda x: x['arrival_time'])
                sb_arrivals.sort(key=lambda x: x['arrival_time'])
                
                # Write column headers
                # Left half of screen - Northbound trains
                draw.text((5, y_pos), "Northbound", font=self.font_small, fill=0)
                # Right half of screen - Southbound trains  
                draw.text((150, y_pos), "Southbound", font=self.font_small, fill=0)
                
                # Draw a vertical line down the middle to separate the two columns
                draw.line((145, 55, 145, 125), fill=0)
                
                # Set up starting positions for writing train times in each column
                nb_y_pos = y_pos + 15  # Northbound starting position (left column)
                sb_y_pos = y_pos + 15  # Southbound starting position (right column)
                
                # We can only fit 4 trains per direction on the screen, so take the first 4
                # [:4] means "take items from position 0 up to (but not including) position 4"
                nb_display = nb_arrivals[:4]
                sb_display = sb_arrivals[:4]
                
                # Go through each northbound train and display it on the left side
                for arrival in nb_display:
                    # Stop if we've run out of room on the screen
                    if nb_y_pos > 120:
                        break
                    
                    # Get information about this train
                    route = arrival['route']  # Which train line (A, C, etc.)
                    minutes = arrival['minutes_until']  # How many minutes until it arrives
                    
                    # Format the time in a nice way
                    if minutes == 0:
                        status = "Now"  # Train is arriving right now!
                    elif minutes == 1:
                        status = "1m"  # One minute away
                    else:
                        status = f"{minutes}m"  # Multiple minutes away (like "5m")
                    
                    # Create the text to display (like "A train: 5m")
                    arrival_text = f"{route} train: {status}"
                    # Write it on the screen in the left column
                    draw.text((10, nb_y_pos), arrival_text, font=self.font_small, fill=0)
                    # Move down 12 pixels for the next train
                    nb_y_pos += 12
                
                # Do the same thing for southbound trains on the right side
                for arrival in sb_display:
                    # Stop if we've run out of room on the screen
                    if sb_y_pos > 120:
                        break
                    
                    # Get information about this train
                    route = arrival['route']  # Which train line
                    minutes = arrival['minutes_until']  # Minutes until arrival
                    
                    # Format the time in a nice way
                    if minutes == 0:
                        status = "Now"
                    elif minutes == 1:
                        status = "1m"
                    else:
                        status = f"{minutes}m"
                    
                    # Create the text to display
                    arrival_text = f"{route} train: {status}"
                    # Write it on the screen in the right column (x position is 155 instead of 10)
                    draw.text((155, sb_y_pos), arrival_text, font=self.font_small, fill=0)
                    # Move down 12 pixels for the next train
                    sb_y_pos += 12
            
            # Rotate the entire image 180 degrees (upside down)
            # This is useful if the screen is mounted upside down physically
            rotated_image = image.transpose(Image.ROTATE_180)
            
            # Send the image to the e-paper display to actually show it
            # getbuffer converts the image into a format the display hardware understands
            self.epd.display(self.epd.getbuffer(rotated_image))
            
        except Exception as e:
            # If anything goes wrong while updating the display, print an error but keep going
            print(f"⚠️  Error displaying on e-paper: {e}")
            traceback.print_exc()  # Print detailed error information for debugging
            print("Display update failed but will continue monitoring...")
    
    def get_all_nostrand_arrivals(self):
        """This is the main function that gets train arrivals and displays them"""
        # This pulls everything together: download data, process it, and show it
        try:
            print("🚇 MTA Live Arrivals - Nostrand Ave-Fulton St Station")
            print("=" * 50)
            print(f"Last updated: {datetime.now().strftime('%I:%M:%S %p')}")
            print()
            
            all_arrivals = {}
            
            # Check ACE feed for A/C lines at Nostrand Ave-Fulton St
            ace_feed = self.fetch_feed_data(self.feeds['ACE'])
            # If we successfully got the data, process it
            if ace_feed:
                # Loop through both platforms (northbound and southbound)
                for station_id, station_name in self.nostrand_stations.items():
                    # Get the arrivals for this specific platform
                    arrivals = self.get_arrivals_for_station(ace_feed, station_id)
                    # If we found any arrivals, save them
                    if arrivals:
                        all_arrivals[station_name] = arrivals
            
            # Display the results in the terminal
            print("\n" + "=" * 50)  # Print a separator line
            # If we didn't find any train arrivals, explain why that might be
            if not all_arrivals:
                print("No arrival data found for Nostrand Ave-Fulton St station.")
                print("This could be due to:")
                print("- Service disruptions")
                print("- Incorrect station IDs")
                print("- API issues")
                print("- Trains not running at this time")
                print("(Script will continue monitoring...)")
            else:
                # If we found arrivals, display them nicely in the terminal
                for station_name, arrivals in all_arrivals.items():
                    # Print the platform name (Northbound or Southbound)
                    print(f"\n📍 {station_name}")
                    print("-" * 40)  # Print a line of dashes
                    
                    # If there are no arrivals for this platform, say so
                    if not arrivals:
                        print("No upcoming arrivals")
                        continue  # Skip to the next platform
                    
                    # Sort arrivals by time and show only the next 5 trains
                    arrivals.sort(key=lambda x: x['arrival_time'])
                    next_arrivals = arrivals[:5]  # Take the first 5 (soonest)
                    
                    # Print each train arrival
                    for arrival in next_arrivals:
                        route = arrival['route']  # Train line (A, C, etc.)
                        time_str = arrival['formatted_time']  # Human-readable time
                        minutes = arrival['minutes_until']  # Minutes from now
                        
                        # Format the countdown in a nice way
                        if minutes == 0:
                            status = "Now"  # Arriving now!
                        elif minutes == 1:
                            status = "1 min"  # Singular
                        else:
                            status = f"{minutes} mins"  # Plural
                        
                        # Print the full arrival information (like "A train: 3:45 PM (5 mins)")
                        print(f"  🚊 {route} train: {time_str} ({status})")
            
            # Update the e-paper screen with the arrivals (or "no data" message)
            # We do this whether we found data or not
            self.display_on_epd(all_arrivals)
            
            # Print a confirmation message so we know the screen was updated
            if not all_arrivals:
                print("✓ E-paper display updated with 'no data' message")
            else:
                # Count up all the arrivals we found
                total_arrivals = sum(len(arrivals) for arrivals in all_arrivals.values())
                print(f"✓ E-paper display updated with {total_arrivals} arrivals")
                
        except Exception as e:
            # If anything goes wrong, print the error but don't stop the program
            print(f"⚠️  Error in get_all_nostrand_arrivals: {e}")
            traceback.print_exc()  # Print detailed error info
            print("Will retry on next update cycle...")
            # Try to update the display with a "no data" message even though there was an error
            try:
                self.display_on_epd({})
            except:
                pass  # If even that fails, just give up and continue
    
    def monitor_arrivals(self, refresh_seconds=30):
        """This function runs forever, checking for new train arrivals every 30 seconds"""
        # This creates a loop that keeps the program running and checking for updates
        print("Starting live monitoring... (Press Ctrl+C to stop)")
        print(f"Refreshing every {refresh_seconds} seconds\n")
        
        while True:
            try:
                self.get_all_nostrand_arrivals()
                print(f"\nNext update in {refresh_seconds} seconds...")
                print("Press Ctrl+C to stop")
                print("=" * 50)
                
                # Wait for the specified number of seconds before checking again
                import time
                time.sleep(refresh_seconds)  # Pause the program
                
                # Clear the terminal screen so the next update looks fresh
                # 'clear' for Mac/Linux, 'cls' for Windows
                os.system('clear' if os.name == 'posix' else 'cls')
                
            except KeyboardInterrupt:
                # If the user presses Ctrl+C, stop the monitoring loop
                print("\n\nMonitoring stopped.")
                self.cleanup()  # Clean up before exiting
                break  # Exit the "while True" loop
            except Exception as e:
                # If any unexpected error happens, don't crash - just report it and try again
                print(f"\n⚠️  Unexpected error in monitor loop: {e}")
                traceback.print_exc()  # Print detailed error info
                print(f"Continuing... will retry in {refresh_seconds} seconds")
                import time
                time.sleep(refresh_seconds)  # Wait before trying again
    
    def cleanup(self):
        """Turn off the e-paper display and close all connections cleanly"""
        # This is like properly shutting down - turning off the screen and closing connections
        # Close the connection to MTA's servers
        try:
            self.session.close()
        except:
            pass  # If it fails, just ignore it and move on
            
        # Properly shut down the e-paper display
        if self.use_epd and self.epd:
            try:
                self.epd.init(self.epd.lut_full_update)  # Initialize for full refresh
                self.epd.Clear(0xFF)  # Clear the screen to white
                self.epd.sleep()  # Put the display into sleep mode to save power
            except Exception as e:
                pass  # If it fails, just ignore it


def main():
    """This is the main function that runs when you start the program"""
    # Think of this as the "start" button for the entire program
    print("MTA Nostrand Ave-Fulton St Live Arrivals")
    print("========================================")
    
    # Create our MTA arrivals object (this sets everything up)
    # use_epd=True means "yes, we want to use the e-paper display"
    mta = MTAArrivals(use_epd=True)
    
    try:
        # Start the continuous monitoring loop
        # This will check for new arrivals every 30 seconds and keep running forever
        # (until we stop it with Ctrl+C)
        mta.monitor_arrivals(30)
    except KeyboardInterrupt:
        # If the user presses Ctrl+C to stop the program
        print("\nShutting down...")
        mta.cleanup()  # Clean up before exiting
    except Exception as e:
        # If any other error happens
        print(f"Error: {e}")
        mta.cleanup()  # Clean up before exiting


# This is a special Python thing that means "run the main() function when this file is started"
# If this file is imported by another program, main() won't run automatically
if __name__ == "__main__":
    main()