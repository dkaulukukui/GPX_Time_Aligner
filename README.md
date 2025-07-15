# GPX File Time Alignment Tool

A Python application with GUI for synchronizing multiple GPX files based on a common geographic alignment point. This tool is perfect for comparing GPS tracks from different devices, aligning race data, or synchronizing route recordings that may have started at different times.

## Features

- 🎯 **Point-Based Alignment**: Align tracks based on any geographic coordinate
- 🔄 **Batch Processing**: Process entire folders of GPX files automatically  
- 🖥️ **User-Friendly GUI**: Intuitive interface with real-time progress updates
- 📊 **Detailed Reporting**: Comprehensive results showing alignment success/failure
- ⚙️ **Configurable Radius**: Set custom search radius around alignment points
- 🕒 **Precise Timing**: Maintains sub-second timestamp precision
- 🔧 **Error Handling**: Robust error handling with informative messages

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Usage Guide](#usage-guide)
- [GUI Interface](#gui-interface)
- [Technical Details](#technical-details)
- [Use Cases](#use-cases)
- [Troubleshooting](#troubleshooting)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Requirements

### System Requirements
- **Python**: 3.7 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 512MB RAM (more for large files)
- **Storage**: Sufficient space for input and output GPX files

### Python Dependencies
- `gpxpy` - GPX file parsing and manipulation
- `tkinter` - GUI framework (usually included with Python)
- Standard library modules: `os`, `sys`, `glob`, `math`, `threading`, `datetime`

## Installation

### 1. Install Python Dependencies

```bash
pip install gpxpy
```

### 2. Download the Script

Save the `gpx_aligner.py` file to your desired directory.

### 3. Verify Installation

```bash
python gpx_aligner.py
```

The GUI should open successfully if all dependencies are installed correctly.

## Quick Start

1. **Launch the application**:
   ```bash
   python gpx_aligner.py
   ```

2. **Configure alignment point**:
   - Enter latitude and longitude coordinates
   - Set search radius (e.g., 100 meters)

3. **Select folders**:
   - Browse and select input folder containing GPX files
   - Browse and select output folder for aligned files

4. **Process files**:
   - Click "Align GPX Files"
   - Monitor progress in the results area

5. **Review results**:
   - Check the results text for successful alignments
   - Find aligned files in your selected output folder

## How It Works

### Alignment Process

1. **Point Detection**: For each GPX file, the tool searches for GPS track points within the specified radius of your alignment coordinates

2. **Reference Time**: The earliest timestamp among all detected alignment points becomes the reference time

3. **Time Adjustment**: Each GPX file's timestamps are shifted so that their alignment point occurs at the reference time

4. **File Output**: Modified GPX files are saved to the output directory with synchronized timestamps

### Example Scenario

Consider three GPS tracks from a running race:
- **Track A**: Passes start line at 10:00:15
- **Track B**: Passes start line at 10:00:22  
- **Track C**: Passes start line at 10:00:08

After alignment:
- **Reference time**: 10:00:08 (earliest)
- **Track A**: Shifted back by 7 seconds
- **Track B**: Shifted back by 14 seconds
- **Track C**: No change (already earliest)

## Usage Guide

### Setting Alignment Coordinates

#### Finding Coordinates
- Use Google Maps: Right-click location → select coordinates
- Use GPS device: Record coordinates at desired alignment point
- Use existing GPX file: Extract coordinates from track points

#### Coordinate Format
- **Latitude**: Decimal degrees (-90 to 90)
- **Longitude**: Decimal degrees (-180 to 180)
- **Example**: `40.7589`, `-73.9851` (Times Square, NYC)

### Choosing Search Radius

| Use Case | Recommended Radius |
|----------|-------------------|
| Race start/finish lines | 10-50 meters |
| Trail intersections | 20-100 meters |
| Geographic landmarks | 50-200 meters |
| General route alignment | 100-500 meters |

### File Organization

#### Input Folder Structure
```
input_folder/
├── track1.gpx
├── track2.gpx
├── track3.GPX
└── other_files.txt (ignored)
```

#### Output Folder Structure  
```
output_folder/
├── track1.gpx (aligned)
├── track2.gpx (aligned)
└── track3.GPX (aligned)
```

## GUI Interface

### Main Sections

#### 1. Alignment Point Configuration
- **Latitude**: Decimal degrees input field
- **Longitude**: Decimal degrees input field  
- **Search Radius**: Distance in meters around alignment point

#### 2. Folder Selection
- **Input Folder**: Browse button to select source directory
- **Output Folder**: Browse button to select destination directory

#### 3. Processing Controls
- **Align GPX Files**: Start processing button
- **Progress Bar**: Visual indication of processing status

#### 4. Results Display
- **Scrollable Text Area**: Real-time progress and detailed results
- **Clear Results**: Button to clear previous results

### Input Validation

The GUI provides comprehensive validation:
- ✅ Coordinate range validation
- ✅ Numeric format checking
- ✅ Folder existence verification
- ✅ Positive radius validation

## Technical Details

### Coordinate System
- Uses **WGS84** coordinate system (standard for GPS)
- Supports decimal degree format only
- Maintains high precision for accurate alignment

### Distance Calculations
- Implements **Haversine formula** for great-circle distances
- Assumes spherical Earth model (radius: 6,371,000 meters)
- Accuracy suitable for GPS track alignment purposes

### Time Precision
- Maintains original timestamp precision from GPX files
- Supports sub-second timing adjustments
- Uses Python's `datetime` and `timedelta` for accurate time arithmetic

### File Processing
- Supports both `.gpx` and `.GPX` file extensions
- Preserves all original GPX data except timestamps
- Creates new files without modifying originals
- Handles malformed GPX files gracefully

### Memory Usage
- Processes files sequentially to minimize memory usage
- Suitable for large collections of GPX files
- Memory usage scales with individual file size, not collection size

## Use Cases

### Sports and Racing
- **Running Races**: Align multiple runner's tracks at start line
- **Cycling Events**: Synchronize different cyclists' recordings
- **Motorsports**: Compare lap times from different timing systems
- **Triathlon**: Align transition point timings

### Route Analysis
- **Hiking Groups**: Synchronize tracks from group members
- **Travel Documentation**: Align tracks from different devices
- **Fleet Management**: Synchronize vehicle route recordings
- **Research**: Align animal tracking data

### Technical Applications
- **GPS Device Testing**: Compare accuracy between devices
- **Time Zone Corrections**: Fix recordings with incorrect time zones
- **Data Integration**: Combine tracks from multiple sources
- **Mapping Projects**: Synchronize survey data collection

## Troubleshooting

### Common Issues

#### No Files Found
**Problem**: "No GPX files found in the specified folder"
**Solutions**:
- Check folder path is correct
- Ensure files have `.gpx` or `.GPX` extension
- Verify folder contains actual GPX files

#### No Alignment Points Found
**Problem**: "No points found within X meters of alignment point"
**Solutions**:
- Increase search radius
- Verify alignment coordinates are correct
- Check if tracks actually pass through the area
- Ensure GPX files contain timestamp data

#### Permission Errors
**Problem**: Cannot write to output folder
**Solutions**:
- Choose different output directory
- Run with administrator privileges
- Check folder write permissions

#### Memory Issues
**Problem**: Application runs slowly or crashes
**Solutions**:
- Process smaller batches of files
- Close other applications
- Use more powerful hardware for large datasets

### Validation Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Latitude must be between -90 and 90" | Invalid latitude | Enter valid decimal degrees |
| "Input folder does not exist" | Wrong folder path | Select existing folder |
| "Radius must be greater than 0" | Invalid radius | Enter positive number |

### File Format Issues

#### Corrupted GPX Files
- Error messages will identify problematic files
- Check GPX file validity with other tools
- Re-export from original GPS device/software

#### Missing Timestamps
- Some GPS devices don't record timestamps
- Tool will skip files without timing data
- Consider adding timestamps manually

## API Documentation

### Core Classes

#### GPXAligner
Main processing class for alignment operations.

**Constructor**: `GPXAligner(alignment_lat, alignment_lon, radius_meters)`

**Key Methods**:
- `align_files(input_folder, output_folder, progress_callback=None)`
- `process_single_file(filepath)`
- `haversine_distance(lat1, lon1, lat2, lon2)`

#### GPXAlignerGUI  
Tkinter-based graphical interface.

**Constructor**: `GPXAlignerGUI(root)`

**Key Methods**:
- `setup_ui()` - Initialize interface components
- `validate_inputs()` - Validate user inputs
- `start_alignment()` - Begin processing

### Return Values

#### align_files() Return Dictionary
```python
{
    'processed': int,        # Total files processed
    'successful': int,       # Successfully aligned files  
    'failed': int,          # Failed files
    'reference_time': datetime,  # Reference timestamp used
    'files': {              # Per-file results
        'filename.gpx': {
            'status': 'success',
            'time_offset': 'timedelta_string',
            'original_alignment_time': datetime,
            'output_path': 'path_string'
        }
    }
}
```

## Contributing

### Development Setup
1. Fork the repository
2. Install development dependencies
3. Create feature branch
4. Make changes with tests
5. Submit pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate  
- Include doxygen-style documentation
- Write comprehensive docstrings

### Testing
- Test with various GPX file formats
- Verify coordinate edge cases
- Test error handling scenarios
- Validate GUI functionality

## License

This project is released under the MIT License. See LICENSE file for details.

## Changelog

### Version 1.0
- Initial release with GUI interface
- Core alignment functionality
- Batch processing support
- Comprehensive error handling
- Real-time progress updates

---

## Support

For issues, feature requests, or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review existing issues in the project repository
3. Create a new issue with detailed information

**When reporting issues, please include**:
- Python version
- Operating system
- Error messages (full text)
- Sample GPX files (if possible)
- Steps to reproduce the problem