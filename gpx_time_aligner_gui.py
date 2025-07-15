#!/usr/bin/env python3
"""
@file gpx_aligner.py
@brief GPX File Time Alignment Script with GUI

@details This script aligns the timing of multiple GPX files based on a common geographic point.
All GPX files will be synchronized so that they all reach the specified alignment point
at the same time. The script provides both a graphical user interface using tkinter
and core alignment functionality for batch processing GPS track files.

@author GPX Alignment Tool
@version 1.0
@date 2025

@section requirements Requirements
- Python 3.7+
- gpxpy library (pip install gpxpy)
- tkinter (usually included with Python)

@section usage Usage
python gpx_aligner.py

@section features Features
- GUI-based alignment point selection
- Batch processing of GPX files
- Configurable search radius
- Real-time progress feedback
- Comprehensive error reporting
- Time offset calculations and display
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
    """
    @brief Core class for aligning GPX file timestamps based on geographic points
    
    @details This class provides functionality to synchronize multiple GPX files by finding
    the closest GPS track points to a specified geographic location and aligning their
    timestamps so all tracks reach that point at the same time.
    """
    
    def __init__(self, alignment_lat: float, alignment_lon: float, radius_meters: float):
        """
        @brief Initialize the GPX aligner with alignment parameters
        
        @param alignment_lat Latitude of the alignment point in decimal degrees (-90 to 90)
        @param alignment_lon Longitude of the alignment point in decimal degrees (-180 to 180)
        @param radius_meters Search radius in meters around the alignment point (must be > 0)
        
        @details Creates a new GPXAligner instance configured with the specified alignment
        point and search radius. The reference time will be determined during processing.
        """
        self.alignment_lat = alignment_lat
        self.alignment_lon = alignment_lon
        self.radius_meters = radius_meters
        self.reference_time = None
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        @brief Calculate the great circle distance between two points on Earth using the Haversine formula
        
        @param lat1 Latitude of the first point in decimal degrees
        @param lon1 Longitude of the first point in decimal degrees
        @param lat2 Latitude of the second point in decimal degrees
        @param lon2 Longitude of the second point in decimal degrees
        
        @return Distance between the two points in meters
        
        @details Uses the Haversine formula to calculate the shortest distance over the earth's
        surface, giving an 'as-the-crow-flies' distance between the points (ignoring any hills,
        valleys, or other obstacles). The Earth's radius is assumed to be 6,371,000 meters.
        
        @note This calculation assumes a spherical Earth model, which provides sufficient
        accuracy for most GPS alignment purposes but may have small errors for very precise
        geodetic calculations.
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
        @brief Find the closest GPS track point to the alignment point within the specified radius
        
        @param gpx_data Parsed GPX data object containing tracks, segments, and points
        
        @return Tuple containing (track_index, segment_index, point_index, timestamp, distance)
                or None if no point is found within the radius
        
        @details Iterates through all tracks, segments, and points in the GPX data to find
        the point that is closest to the alignment coordinates and within the search radius.
        Only considers points that have valid timestamps.
        
        @note If multiple points are equidistant from the alignment point, the first one
        encountered in the iteration order will be returned.
        
        @throws None - method handles all internal exceptions gracefully
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
        @brief Adjust all timestamps in the GPX data by the specified time offset
        
        @param gpx_data GPX data object to modify
        @param time_offset Time offset to add to all timestamps (can be negative)
        
        @details Iterates through all tracks, segments, and points in the GPX data,
        adjusting each timestamp by the specified offset. Points without timestamps
        are left unchanged.
        
        @warning This method modifies the GPX data in-place. Make a copy before calling
        if you need to preserve the original timestamps.
        
        @note The time_offset parameter uses Python's timedelta object, allowing for
        precise time adjustments including sub-second precision.
        """
        for track in gpx_data.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if point.time is not None:
                        point.time += time_offset
    
    def process_single_file(self, filepath: str) -> Tuple[bool, str, Optional[datetime]]:
        """
        @brief Process a single GPX file to find its alignment point
        
        @param filepath Full path to the GPX file to process
        
        @return Tuple containing (success_flag, status_message, alignment_timestamp)
                - success_flag: True if alignment point found, False otherwise
                - status_message: Human-readable description of the result
                - alignment_timestamp: datetime when the track passes closest to alignment point, or None
        
        @details Opens and parses the specified GPX file, then searches for the closest
        point to the alignment coordinates within the search radius. This method is used
        during the analysis phase before actual alignment occurs.
        
        @throws Returns error information in the status message rather than raising exceptions
        
        @note This method only analyzes the file without modifying it. The actual time
        adjustment happens in the align_files method.
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
        @brief Align all GPX files in the input folder and save synchronized versions
        
        @param input_folder Path to folder containing GPX files to process
        @param output_folder Path to folder where aligned GPX files will be saved
        @param progress_callback Optional callback function for progress updates (default: None)
        
        @return Dictionary containing alignment results with the following structure:
                - 'processed': Total number of files processed
                - 'successful': Number of files successfully aligned
                - 'failed': Number of files that failed processing
                - 'reference_time': The reference timestamp used for alignment
                - 'files': Dict mapping filenames to their individual results
                - 'error': Error message if fatal error occurred
        
        @details This is the main processing method that:
        1. Scans the input folder for GPX files (*.gpx, *.GPX)
        2. Analyzes each file to find alignment points
        3. Determines the earliest alignment time as reference
        4. Adjusts timestamps in each file and saves aligned versions
        
        @note The progress_callback function, if provided, should accept a single string
        parameter containing the progress message to display.
        
        @throws Returns error information in result dictionary rather than raising exceptions
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
    """
    @brief Tkinter-based graphical user interface for the GPX alignment tool
    
    @details Provides a user-friendly interface for configuring alignment parameters,
    selecting input/output folders, and monitoring the alignment process. The GUI
    includes input validation, progress tracking, and comprehensive results display.
    
    @section gui_features GUI Features
    - Alignment point coordinate input with validation
    - Folder selection dialogs for input/output directories
    - Real-time progress updates during processing
    - Scrollable results display
    - Background processing to maintain UI responsiveness
    """
    
    def __init__(self, root):
        """
        @brief Initialize the GUI application
        
        @param root The main tkinter window object
        
        @details Sets up all GUI components, initializes variables, and configures
        the main window properties including size and title.
        """
        self.root = root
        self.root.title("GPX File Time Alignment Tool")
        self.root.geometry("800x700")
        
        # Variables
        self.input_folder = tk.StringVar(value = ".\in")
        self.output_folder = tk.StringVar(value = ".\out")
        self.latitude = tk.DoubleVar(value=21.2708890)
        self.longitude = tk.DoubleVar(value=-157.7161200)
        self.radius = tk.DoubleVar(value=200.0)
        
        self.setup_ui()
    
    def setup_ui(self):
        """
        @brief Create and configure all GUI components
        
        @details Builds the complete user interface including:
        - Title and main layout frames
        - Alignment point input section (latitude, longitude, radius)
        - Folder selection section (input/output directories)
        - Process button and progress bar
        - Results display area with scrollable text
        
        @note Uses ttk widgets for modern appearance and proper theming support
        """
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
        """
        @brief Open file dialog to select input folder containing GPX files
        
        @details Uses tkinter's askdirectory dialog to allow user selection of the
        input folder. Updates the input_folder StringVar with the selected path.
        """
        folder = filedialog.askdirectory(title="Select folder containing GPX files")
        if folder:
            self.input_folder.set(folder)
    
    def select_output_folder(self):
        """
        @brief Open file dialog to select output folder for aligned GPX files
        
        @details Uses tkinter's askdirectory dialog to allow user selection of the
        output folder. Updates the output_folder StringVar with the selected path.
        """
        folder = filedialog.askdirectory(title="Select output folder for aligned GPX files")
        if folder:
            self.output_folder.set(folder)
    
    def validate_inputs(self):
        """
        @brief Validate all user inputs before processing
        
        @return True if all inputs are valid, False otherwise
        
        @details Performs comprehensive validation including:
        - Input/output folder existence and selection
        - Latitude range validation (-90 to 90 degrees)
        - Longitude range validation (-180 to 180 degrees)  
        - Radius value validation (must be positive)
        - Numeric format validation for all coordinate fields
        
        @note Displays appropriate error messages for any validation failures
        """
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
        """
        @brief Add progress message to the results text area
        
        @param message String message to display in the results area
        
        @details Appends the message to the scrollable text widget and automatically
        scrolls to show the latest content. Updates the GUI to ensure immediate display.
        """
        self.results_text.insert(tk.END, message)
        self.results_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_results(self):
        """
        @brief Clear all content from the results text area
        
        @details Removes all text from the scrollable results display, providing
        a clean slate for new processing runs.
        """
        self.results_text.delete(1.0, tk.END)
    
    def start_alignment(self):
        """
        @brief Initiate the GPX alignment process with input validation
        
        @details Validates all user inputs, creates the output directory if needed,
        and starts the alignment process in a background thread to maintain GUI
        responsiveness. Disables the process button and starts the progress bar
        during processing.
        
        @note This method performs validation and setup, then delegates actual
        processing to run_alignment() in a separate thread.
        """
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
        """
        @brief Execute the GPX alignment process in a background thread
        
        @details This method runs in a separate thread to prevent GUI freezing during
        file processing. It creates a GPXAligner instance, processes all files in the
        input directory, and provides real-time progress updates through the GUI.
        
        @note This method should only be called from start_alignment() to ensure proper
        thread management and GUI state handling.
        
        @warning Must call finish_alignment() when complete to restore GUI state
        """
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
        """
        @brief Clean up GUI state after alignment process completes
        
        @details Stops the progress bar animation and re-enables the process button
        to allow for additional alignment operations. This method is called from the
        main thread to ensure proper GUI updates.
        """
        self.progress.stop()
        self.process_btn.config(state="normal")


def main():
    """
    @brief Main entry point for the GUI application
    
    @details Initializes the tkinter root window, configures modern styling themes,
    creates the GPXAlignerGUI instance, and starts the main event loop.
    
    @note Attempts to use modern themes (clam, alt) if available for better appearance
    """
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
