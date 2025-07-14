#!/usr/bin/env python3
"""
GPX File Time Alignment Script with GUI

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
import threading
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    import gpxpy
    import gpxpy.gpx
except ImportError:
    messagebox.showerror("Missing Dependency", 
                        "gpxpy library is required.\n\nInstall it with: pip install gpxpy")
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
    
    def align_files(self, input_folder: str, output_folder: str, progress_callback=None) -> dict:
        """
        Align all GPX files in the input folder.
        
        Args:
            input_folder: Path to folder containing GPX files
            output_folder: Path to output folder
            progress_callback: Function to call with progress updates
        
        Returns:
            Dictionary with alignment results
        """
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
        
        if progress_callback:
            progress_callback(f"Found {len(gpx_files)} GPX files\n")
        
        # First pass: find alignment times for all files
        file_info = {}
        alignment_times = []
        
        for i, filepath in enumerate(gpx_files):
            filename = os.path.basename(filepath)
            if progress_callback:
                progress_callback(f"Analyzing {filename}...\n")
            
            success, message, alignment_time = self.process_single_file(filepath)
            file_info[filepath] = {
                'success': success,
                'message': message,
                'alignment_time': alignment_time,
                'filename': filename
            }
            
            if success and alignment_time:
                alignment_times.append(alignment_time)
            
            if progress_callback:
                progress_callback(f"  {message}\n")
        
        if not alignment_times:
            return {'error': 'No files had points within the specified radius of the alignment point'}
        
        # Use the earliest alignment time as reference
        self.reference_time = min(alignment_times)
        if progress_callback:
            progress_callback(f"\nUsing reference time: {self.reference_time}\n\n")
        
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
                
                if progress_callback:
                    progress_callback(f"Aligned {filename} (offset: {time_offset})\n")
                
            except Exception as e:
                results['failed'] += 1
                results['files'][filename] = {
                    'status': 'failed',
                    'message': f"Error during alignment: {str(e)}"
                }
                if progress_callback:
                    progress_callback(f"Failed to align {filename}: {str(e)}\n")
        
        return results


class GPXAlignerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GPX File Time Alignment Tool")
        self.root.geometry("800x700")
        
        # Variables
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.latitude = tk.DoubleVar(value=0.0)
        self.longitude = tk.DoubleVar(value=0.0)
        self.radius = tk.DoubleVar(value=100.0)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="GPX File Time Alignment Tool", 
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Alignment Point Section
        alignment_frame = ttk.LabelFrame(main_frame, text="Alignment Point", padding="10")
        alignment_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        alignment_frame.columnconfigure(1, weight=1)
        
        # Latitude
        ttk.Label(alignment_frame, text="Latitude:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        lat_entry = ttk.Entry(alignment_frame, textvariable=self.latitude, width=15)
        lat_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 20))
        
        # Longitude
        ttk.Label(alignment_frame, text="Longitude:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        lon_entry = ttk.Entry(alignment_frame, textvariable=self.longitude, width=15)
        lon_entry.grid(row=0, column=3, sticky=(tk.W, tk.E))
        
        # Radius
        ttk.Label(alignment_frame, text="Search Radius (meters):").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        radius_entry = ttk.Entry(alignment_frame, textvariable=self.radius, width=15)
        radius_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Folder Selection Section
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding="10")
        folder_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)
        
        # Input folder
        ttk.Label(folder_frame, text="Input Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        input_entry = ttk.Entry(folder_frame, textvariable=self.input_folder, state="readonly")
        input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(folder_frame, text="Browse...", 
                  command=self.select_input_folder).grid(row=0, column=2)
        
        # Output folder
        ttk.Label(folder_frame, text="Output Folder:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        output_entry = ttk.Entry(folder_frame, textvariable=self.output_folder, state="readonly")
        output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=(10, 0))
        ttk.Button(folder_frame, text="Browse...", 
                  command=self.select_output_folder).grid(row=1, column=2, pady=(10, 0))
        
        # Process button
        process_frame = ttk.Frame(main_frame)
        process_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))
        
        self.process_btn = ttk.Button(process_frame, text="Align GPX Files", 
                                     command=self.start_alignment, style="Accent.TButton")
        self.process_btn.pack(pady=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Results text area
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=15, width=80)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear results button
        ttk.Button(results_frame, text="Clear Results", 
                  command=self.clear_results).grid(row=1, column=0, pady=(10, 0))
    
    def select_input_folder(self):
        """Open dialog to select input folder."""
        folder = filedialog.askdirectory(title="Select folder containing GPX files")
        if folder:
            self.input_folder.set(folder)
    
    def select_output_folder(self):
        """Open dialog to select output folder."""
        folder = filedialog.askdirectory(title="Select output folder for aligned GPX files")
        if folder:
            self.output_folder.set(folder)
    
    def validate_inputs(self):
        """Validate user inputs."""
        if not self.input_folder.get():
            messagebox.showerror("Input Error", "Please select an input folder")
            return False
        
        if not os.path.exists(self.input_folder.get()):
            messagebox.showerror("Input Error", "Input folder does not exist")
            return False
        
        if not self.output_folder.get():
            messagebox.showerror("Input Error", "Please select an output folder")
            return False
        
        try:
            lat = self.latitude.get()
            lon = self.longitude.get()
            radius = self.radius.get()
            
            if not (-90 <= lat <= 90):
                messagebox.showerror("Input Error", "Latitude must be between -90 and 90")
                return False
            
            if not (-180 <= lon <= 180):
                messagebox.showerror("Input Error", "Longitude must be between -180 and 180")
                return False
            
            if radius <= 0:
                messagebox.showerror("Input Error", "Radius must be greater than 0")
                return False
                
        except tk.TclError:
            messagebox.showerror("Input Error", "Please enter valid numeric values for coordinates and radius")
            return False
        
        return True
    
    def log_progress(self, message):
        """Add message to results text area."""
        self.results_text.insert(tk.END, message)
        self.results_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_results(self):
        """Clear the results text area."""
        self.results_text.delete(1.0, tk.END)
    
    def start_alignment(self):
        """Start the alignment process in a separate thread."""
        if not self.validate_inputs():
            return
        
        # Create output folder if it doesn't exist
        try:
            os.makedirs(self.output_folder.get(), exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create output folder: {str(e)}")
            return
        
        # Disable process button and start progress bar
        self.process_btn.config(state="disabled")
        self.progress.start()
        
        # Clear previous results
        self.clear_results()
        
        # Start alignment in separate thread
        alignment_thread = threading.Thread(target=self.run_alignment)
        alignment_thread.daemon = True
        alignment_thread.start()
    
    def run_alignment(self):
        """Run the alignment process."""
        try:
            # Create aligner
            aligner = GPXAligner(
                self.latitude.get(),
                self.longitude.get(),
                self.radius.get()
            )
            
            self.log_progress(f"Starting GPX file alignment...\n")
            self.log_progress(f"Alignment point: {self.latitude.get()}, {self.longitude.get()}\n")
            self.log_progress(f"Search radius: {self.radius.get()}m\n")
            self.log_progress(f"Input folder: {self.input_folder.get()}\n")
            self.log_progress(f"Output folder: {self.output_folder.get()}\n\n")
            
            # Process files
            results = aligner.align_files(
                self.input_folder.get(),
                self.output_folder.get(),
                self.log_progress
            )
            
            # Display results
            self.log_progress("\n" + "="*50 + "\n")
            self.log_progress("ALIGNMENT RESULTS\n")
            self.log_progress("="*50 + "\n")
            
            if 'error' in results:
                self.log_progress(f"Error: {results['error']}\n")
            else:
                self.log_progress(f"Files processed: {results['processed']}\n")
                self.log_progress(f"Successfully aligned: {results['successful']}\n")
                self.log_progress(f"Failed: {results['failed']}\n")
                self.log_progress(f"Reference time: {results['reference_time']}\n")
                
                if results['successful'] > 0:
                    self.log_progress(f"\nAligned files saved to: {self.output_folder.get()}\n")
                    
                    # Show summary of successful files
                    self.log_progress("\nSuccessfully aligned files:\n")
                    for filename, info in results['files'].items():
                        if info['status'] == 'success':
                            self.log_progress(f"  {filename} (offset: {info['time_offset']})\n")
                
                if results['failed'] > 0:
                    self.log_progress("\nFailed files:\n")
                    for filename, info in results['files'].items():
                        if info['status'] == 'failed':
                            self.log_progress(f"  {filename}: {info['message']}\n")
        
        except Exception as e:
            self.log_progress(f"\nUnexpected error: {str(e)}\n")
        
        finally:
            # Re-enable process button and stop progress bar
            self.root.after(0, self.finish_alignment)
    
    def finish_alignment(self):
        """Clean up after alignment process completes."""
        self.progress.stop()
        self.process_btn.config(state="normal")


def main():
    """Main function to start the GUI application."""
    root = tk.Tk()
    
    # Set up modern styling
    style = ttk.Style()
    
    # Try to use a modern theme if available
    available_themes = style.theme_names()
    if 'clam' in available_themes:
        style.theme_use('clam')
    elif 'alt' in available_themes:
        style.theme_use('alt')
    
    app = GPXAlignerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
