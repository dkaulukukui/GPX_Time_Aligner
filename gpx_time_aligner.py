#!/usr/bin/env python3
"""
GPX File Time Alignment Script

This script aligns the timing of multiple GPX files based on a common geographic point.
All GPX files will be synchronized so that they all reach the specified alignment point
at the same time.

Requirements:
    pip install gpxpy

Usage:
    python gpx_aligner.py
"""

import os
import sys
import glob
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import math

try:
    import gpxpy
    import gpxpy.gpx
except ImportError:
    print("Error: gpxpy library is required. Install it with: pip install gpxpy")
    sys.exit(1)


class GPXAligner:
    def __init__(self, alignment_lat: float, alignment_lon: float, radius_meters: float):
        """
        Initialize the GPX aligner.
        
        Args:
            alignment_lat: Latitude of the alignment point
            alignment_lon: Longitude of the alignment point
            radius_meters: Search radius in meters around the alignment point
        """
        self.alignment_lat = alignment_lat
        self.alignment_lon = alignment_lon
        self.radius_meters = radius_meters
        self.reference_time = None
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        
        Returns:
            Distance in meters
        """
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def find_closest_point_in_radius(self, gpx_data) -> Optional[Tuple[int, int, datetime, float]]:
        """
        Find the closest point to the alignment point within the specified radius.
        
        Returns:
            Tuple of (track_index, point_index, timestamp, distance) or None if no point found
        """
        closest_distance = float('inf')
        closest_info = None
        
        for track_idx, track in enumerate(gpx_data.tracks):
            for segment_idx, segment in enumerate(track.segments):
                for point_idx, point in enumerate(segment.points):
                    if point.time is None:
                        continue
                    
                    distance = self.haversine_distance(
                        self.alignment_lat, self.alignment_lon,
                        point.latitude, point.longitude
                    )
                    
                    if distance <= self.radius_meters and distance < closest_distance:
                        closest_distance = distance
                        closest_info = (track_idx, segment_idx, point_idx, point.time, distance)
        
        return closest_info
    
    def adjust_gpx_timing(self, gpx_data, time_offset: timedelta):
        """
        Adjust all timestamps in the GPX data by the given offset.
        """
        for track in gpx_data.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if point.time is not None:
                        point.time += time_offset
    
    def process_single_file(self, filepath: str) -> Tuple[bool, str, Optional[datetime]]:
        """
        Process a single GPX file and find its alignment point.
        
        Returns:
            Tuple of (success, message, alignment_time)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as gpx_file:
                gpx_data = gpxpy.parse(gpx_file)
            
            closest_info = self.find_closest_point_in_radius(gpx_data)
            
            if closest_info is None:
                return False, f"No points found within {self.radius_meters}m of alignment point", None
            
            track_idx, segment_idx, point_idx, alignment_time, distance = closest_info
            
            return True, f"Found alignment point at distance {distance:.1f}m", alignment_time
            
        except Exception as e:
            return False, f"Error processing file: {str(e)}", None
    
    def align_files(self, input_folder: str, output_folder: str = None) -> dict:
        """
        Align all GPX files in the input folder.
        
        Args:
            input_folder: Path to folder containing GPX files
            output_folder: Path to output folder (defaults to input_folder + '_aligned')
        
        Returns:
            Dictionary with alignment results
        """
        if output_folder is None:
            output_folder = input_folder.rstrip('/\\') + '_aligned'
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Find all GPX files
        gpx_patterns = [
            os.path.join(input_folder, '*.gpx'),
            os.path.join(input_folder, '*.GPX')
        ]
        
        gpx_files = []
        for pattern in gpx_patterns:
            gpx_files.extend(glob.glob(pattern))
        
        if not gpx_files:
            return {'error': 'No GPX files found in the specified folder'}
        
        print(f"Found {len(gpx_files)} GPX files")
        
        # First pass: find alignment times for all files
        file_info = {}
        alignment_times = []
        
        for filepath in gpx_files:
            filename = os.path.basename(filepath)
            print(f"Analyzing {filename}...")
            
            success, message, alignment_time = self.process_single_file(filepath)
            file_info[filepath] = {
                'success': success,
                'message': message,
                'alignment_time': alignment_time,
                'filename': filename
            }
            
            if success and alignment_time:
                alignment_times.append(alignment_time)
            
            print(f"  {message}")
        
        if not alignment_times:
            return {'error': 'No files had points within the specified radius of the alignment point'}
        
        # Use the earliest alignment time as reference
        self.reference_time = min(alignment_times)
        print(f"\nUsing reference time: {self.reference_time}")
        
        # Second pass: align and save files
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'reference_time': self.reference_time,
            'files': {}
        }
        
        for filepath in gpx_files:
            info = file_info[filepath]
            filename = info['filename']
            
            results['processed'] += 1
            
            if not info['success']:
                results['failed'] += 1
                results['files'][filename] = {
                    'status': 'failed',
                    'message': info['message']
                }
                continue
            
            try:
                # Load and process the file
                with open(filepath, 'r', encoding='utf-8') as gpx_file:
                    gpx_data = gpxpy.parse(gpx_file)
                
                # Calculate time offset needed
                time_offset = self.reference_time - info['alignment_time']
                
                # Adjust timing
                self.adjust_gpx_timing(gpx_data, time_offset)
                
                # Save aligned file
                output_path = os.path.join(output_folder, filename)
                with open(output_path, 'w', encoding='utf-8') as output_file:
                    output_file.write(gpx_data.to_xml())
                
                results['successful'] += 1
                results['files'][filename] = {
                    'status': 'success',
                    'time_offset': str(time_offset),
                    'original_alignment_time': info['alignment_time'],
                    'output_path': output_path
                }
                
                print(f"Aligned {filename} (offset: {time_offset})")
                
            except Exception as e:
                results['failed'] += 1
                results['files'][filename] = {
                    'status': 'failed',
                    'message': f"Error during alignment: {str(e)}"
                }
                print(f"Failed to align {filename}: {str(e)}")
        
        return results


def main():
    """Main function with user interface."""
    print("GPX File Time Alignment Tool")
    print("=" * 40)
    
    # Get alignment point coordinates
    try:
        lat = float(input("Enter alignment point latitude: "))
        lon = float(input("Enter alignment point longitude: "))
        radius = float(input("Enter search radius in meters: "))
    except ValueError:
        print("Error: Please enter valid numeric values")
        return
    
    # Get input folder
    input_folder = input("Enter path to folder containing GPX files: ").strip()
    if not os.path.exists(input_folder):
        print(f"Error: Folder '{input_folder}' does not exist")
        return
    
    # Get output folder (optional)
    output_folder = input("Enter output folder path (press Enter for default): ").strip()
    if not output_folder:
        output_folder = None
    
    # Create aligner and process files
    aligner = GPXAligner(lat, lon, radius)
    
    print(f"\nProcessing GPX files...")
    print(f"Alignment point: {lat}, {lon}")
    print(f"Search radius: {radius}m")
    print(f"Input folder: {input_folder}")
    
    results = aligner.align_files(input_folder, output_folder)
    
    # Display results
    print("\n" + "=" * 50)
    print("ALIGNMENT RESULTS")
    print("=" * 50)
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return
    
    print(f"Files processed: {results['processed']}")
    print(f"Successfully aligned: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Reference time: {results['reference_time']}")
    
    if results['successful'] > 0:
        output_dir = output_folder or (input_folder.rstrip('/\\') + '_aligned')
        print(f"\nAligned files saved to: {output_dir}")
    
    # Show detailed results
    if input("\nShow detailed results? (y/n): ").lower().startswith('y'):
        print("\nDetailed Results:")
        print("-" * 30)
        for filename, info in results['files'].items():
            print(f"\n{filename}:")
            print(f"  Status: {info['status']}")
            if info['status'] == 'success':
                print(f"  Time offset: {info['time_offset']}")
                print(f"  Original alignment time: {info['original_alignment_time']}")
            else:
                print(f"  Message: {info['message']}")


if __name__ == "__main__":
    main()
