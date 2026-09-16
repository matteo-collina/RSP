#!/usr/bin/env python3
"""
Process Metashape Reference Export File

This script processes a manually exported reference file from Metashape
to extract estimated baseline distances and calculate the median.

Usage: Run this script within Agisoft Metashape Python console
"""

import sys
import statistics
import os
from datetime import datetime

# Try to import Metashape for dialog functionality
try:
    import Metashape
    METASHAPE_AVAILABLE = True
except ImportError:
    METASHAPE_AVAILABLE = False


def process_reference_export(file_path):
    """
    Process the manually exported reference file to extract estimated distances.
    
    Args:
        file_path: Path to the exported reference file
        
    Returns:
        List of estimated distances in meters
    """
    distances = []
    
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            
        print(f"Processing file: {file_path}")
        print(f"Found {len(lines)} lines")
        
        stereo_distances = []
        other_scalebars = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if line.startswith('#') or not line:
                continue
            
            # Split by comma
            parts = line.split(',')
            
            if len(parts) >= 3:
                label = parts[0].strip()
                distance_set = parts[1].strip()  # Set distance
                distance_est = parts[2].strip()  # Estimated distance
                
                # Check if this is a stereo pair scalebar
                # Stereo pairs contain both "_left_" and "_right_" in the label
                if "_left_" in label and "_right_" in label:
                    # This is a stereo pair scalebar
                    if distance_est and distance_est != '':
                        try:
                            est_value = float(distance_est)
                            stereo_distances.append(est_value)
                            print(f"Stereo pair: {label} -> {est_value:.6f} m")
                        except ValueError:
                            print(f"Warning: Could not parse estimated distance '{distance_est}' for {label}")
                else:
                    # This is some other scalebar (like targets)
                    other_scalebars.append(label)
        
        print(f"\nSummary:")
        print(f"- Stereo pair scalebars found: {len(stereo_distances)}")
        print(f"- Other scalebars (ignored): {len(other_scalebars)}")
        
        if other_scalebars:
            print(f"- Ignored scalebars: {other_scalebars}")
        
        return stereo_distances
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return []


def run_metashape_version():
    """Run the script with Metashape dialogs."""
    try:
        # Ask user to select the reference export file
        export_file = Metashape.app.getOpenFileName("Select Reference Export File", 
                                                   filter="Text files (*.txt);;CSV files (*.csv);;All files (*.*)")
        
        if not export_file:
            print("No file selected. Operation cancelled.")
            return
        
        print(f"Selected export file: {export_file}")
        
        # Process the export file
        distances = process_reference_export(export_file)
        
        if not distances:
            Metashape.app.messageBox("No stereo pair distances found in the export file.\n\nMake sure:\n" +
                                   "1. The file contains scalebars with '_left_' and '_right_' in their names\n" +
                                   "2. The estimated distances are in the third column\n" +
                                   "3. The file format matches the expected TXT structure")
            return
        
        # Calculate statistics
        unique_distances = []
        seen = set()
        for d in distances:
            if d not in seen:
                unique_distances.append(d)
                seen.add(d)
        
        median_distance = statistics.median(unique_distances)
        mean_distance = statistics.mean(unique_distances)
        std_dev = statistics.stdev(unique_distances) if len(unique_distances) > 1 else 0.0
        min_distance = min(unique_distances)
        max_distance = max(unique_distances)
        cv = (std_dev / median_distance) * 100 if median_distance > 0 else 0
        
        # Generate results report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        results_text = f"""STEREO BASELINE CALIBRATION RESULTS
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Export file: {os.path.basename(export_file)}

MEASUREMENTS:
Total measurements: {len(distances)}
Unique measurements: {len(unique_distances)}

BASELINE DISTANCE:
Median: {median_distance:.6f} m  <- RECOMMENDED
Mean: {mean_distance:.6f} m
Standard deviation: {std_dev:.6f} m
Range: {min_distance:.6f} m to {max_distance:.6f} m

QUALITY ASSESSMENT:
Coefficient of variation: {cv:.2f}%
"""
        
        if cv < 2.0:
            quality_status = "Excellent consistency (CV < 2%)"
        elif cv < 5.0:
            quality_status = "Good consistency (CV < 5%)"
        elif cv < 10.0:
            quality_status = "Moderate consistency (CV < 10%) - consider recalibration"
        else:
            quality_status = "High variation (CV ≥ 10%) - recalibrate cameras"
        
        results_text += f"Status: {quality_status}\n\n"
        
        results_text += "ALL UNIQUE MEASUREMENTS:\n"
        for i, d in enumerate(sorted(unique_distances), 1):
            results_text += f"  {i:2d}. {d:.6f} m\n"
        
        # Ask user where to save the results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"calibration_{timestamp}.txt"
        
        save_file = Metashape.app.getSaveFileName("Save Calibration Results", 
                                                filter="Text files (*.txt);;All files (*.*)")
        
        # If user didn't specify an extension, add .txt
        if save_file and not save_file.endswith('.txt'):
            save_file += '.txt'
        
        if not save_file:
            # Show results in message box if user doesn't want to save
            Metashape.app.messageBox(f"Results (not saved):\n\n{results_text[:500]}...")
            print("\nResults not saved (user cancelled save dialog)")
            print("="*60)
            print(results_text)
            return
        
        # Save results to file
        try:
            with open(save_file, 'w') as f:
                f.write(results_text)
            
            success_message = f"BASELINE DISTANCE: {median_distance:.6f} m"
            
            print("="*60)
            print("CALIBRATION RESULTS SAVED")
            print("="*60)
            print(results_text)
            
            Metashape.app.messageBox(success_message)
            
        except Exception as e:
            error_msg = f"Error saving results: {str(e)}"
            print(error_msg)
            Metashape.app.messageBox(error_msg)
        
    except Exception as e:
        error_msg = f"Error in Metashape version: {str(e)}"
        print(error_msg)
        if METASHAPE_AVAILABLE:
            Metashape.app.messageBox(error_msg)


def main():
    """Main function - detects if running in Metashape or command line."""
    
    # Check if running in Metashape (no command line arguments and Metashape available)
    if METASHAPE_AVAILABLE and len(sys.argv) == 1:
        print("Running in Metashape mode with dialogs...")
        run_metashape_version()
        return
    
    # Command line mode
    if len(sys.argv) != 2:
        print("STEREO BASELINE CALIBRATION PROCESSOR")
        print("="*50)
        print("Usage:")
        print("  In Metashape: Run directly in Python console (uses dialogs)")
        print("  Command line: python process_reference_export.py <export_file_path>")
        print("\nExample:")
        print("  python process_reference_export.py report.txt")
        return
    
    file_path = sys.argv[1]
    
    # Process the export file
    distances = process_reference_export(file_path)
    
    if distances:
        # Remove duplicates while preserving order
        unique_distances = []
        seen = set()
        for d in distances:
            if d not in seen:
                unique_distances.append(d)
                seen.add(d)
        
        median_distance = statistics.median(unique_distances)
        mean_distance = statistics.mean(unique_distances)
        std_dev = statistics.stdev(unique_distances) if len(unique_distances) > 1 else 0.0
        min_distance = min(unique_distances)
        max_distance = max(unique_distances)
        
        print(f"\n" + "="*50)
        print("STEREO BASELINE ANALYSIS RESULTS")
        print("="*50)
        print(f"Total measurements: {len(distances)}")
        print(f"Unique measurements: {len(unique_distances)}")
        print(f"")
        print(f"MEDIAN BASELINE DISTANCE: {median_distance:.6f} m  <- RECOMMENDED")
        print(f"Mean distance:            {mean_distance:.6f} m")
        print(f"Standard deviation:       {std_dev:.6f} m")
        print(f"Range: {min_distance:.6f} m to {max_distance:.6f} m")
        print(f"")
        print(f"All unique measurements:")
        for i, d in enumerate(sorted(unique_distances), 1):
            print(f"  {i:2d}. {d:.6f} m")
        
        # Quality assessment
        cv = (std_dev / median_distance) * 100 if median_distance > 0 else 0
        print(f"\nQuality Assessment:")
        print(f"Coefficient of variation: {cv:.2f}%")
        
        if cv < 2.0:
            print("Excellent consistency (CV < 2%)")
        elif cv < 5.0:
            print("Good consistency (CV < 5%)")
        elif cv < 10.0:
            print("Moderate consistency (CV < 10%) - consider recalibration")
        else:
            print("High variation (CV ≥ 10%) - recalibrate cameras")
            
    else:
        print("\nNo stereo pair distances found in the export file.")
        print("Make sure:")
        print("1. The file contains scalebars with '_left_' and '_right_' in their names")
        print("2. The estimated distances are in the third column")
        print("3. The file format matches the expected TXT structure")


if __name__ == "__main__":
    main()
