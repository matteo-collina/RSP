#!/usr/bin/env python3
"""
Agisoft Metashape Stereo Scalebar Creation Script

This script:
1. Finds stereo camera pairs (left/right naming convention)
2. Creates scalebars between stereo pairs
3. Updates the scene so estimated distances can be calculated

Usage: Run this script within Agisoft Metashape Python console
"""

import Metashape


def find_stereo_pairs(cameras):
    """
    Find stereo camera pairs based on naming convention.
    
    Expected naming: prefix_left_number and prefix_right_number
    
    Args:
        cameras: List of Metashape cameras
        
    Returns:
        List of tuples (left_camera, right_camera)
    """
    pairs = []
    left_cameras = {}
    right_cameras = {}
    
    # Separate cameras into left and right groups
    for camera in cameras:
        if camera.type != Metashape.Camera.Type.Regular:
            continue
            
        parts = camera.label.split("_")
        
        # Ensure the label has enough parts to process (at least 3: prefix, side, number)
        if len(parts) >= 3:
            prefix = "_".join(parts[:-2])  # Everything except last two parts
            side = parts[-2]               # Second to last part (left/right)
            number = parts[-1]             # Last part (number)
            
            key = f"{prefix}_{number}"     # Unique identifier for the pair
            
            if side.lower() == "left":
                left_cameras[key] = camera
            elif side.lower() == "right":
                right_cameras[key] = camera
    
    # Match left and right cameras
    for key in left_cameras:
        if key in right_cameras:
            pairs.append((left_cameras[key], right_cameras[key]))
    
    return pairs


def create_scalebars_for_pairs(chunk, stereo_pairs):
    """
    Create scalebars between stereo camera pairs.
    
    Args:
        chunk: Metashape chunk
        stereo_pairs: List of (left_camera, right_camera) tuples
        
    Returns:
        List of created scalebars
    """
    created_scalebars = []
    
    for left_camera, right_camera in stereo_pairs:
        try:
            # Create scalebar between the stereo pair
            scalebar = chunk.addScalebar(left_camera, right_camera)
            created_scalebars.append(scalebar)
            print(f"Created scalebar between {left_camera.label} and {right_camera.label}")
        except Exception as e:
            print(f"Error creating scalebar for {left_camera.label} - {right_camera.label}: {e}")
    
    return created_scalebars


def create_stereo_scalebars():
    """Main function to create scalebars for stereo camera pairs."""
    try:
        chunk = Metashape.app.document.chunk
        
        if not chunk:
            Metashape.app.messageBox("No active chunk found. Please open a project first.")
            return
        
        # Get cameras
        cameras = [camera for camera in chunk.cameras if camera.type == Metashape.Camera.Type.Regular]
        
        if not cameras:
            Metashape.app.messageBox("No cameras found in the chunk.")
            return
        
        print(f"Found {len(cameras)} cameras")
        
        # Find stereo pairs
        stereo_pairs = find_stereo_pairs(cameras)
        
        if not stereo_pairs:
            Metashape.app.messageBox("No stereo camera pairs found.\nExpected naming: prefix_left_number and prefix_right_number")
            return
        
        print(f"Found {len(stereo_pairs)} stereo pairs")
        
        # Create scalebars
        created_scalebars = create_scalebars_for_pairs(chunk, stereo_pairs)
        
        if not created_scalebars:
            Metashape.app.messageBox("No scalebars could be created.")
            return
        
        print(f"Created {len(created_scalebars)} scalebars")
        
        # Update scene so estimated distances can be calculated
        print("Updating scene to calculate estimated distances...")
        chunk.updateTransform()
        
        # Success message
        result_message = f"""Scalebar Creation Complete!

Stereo pairs found: {len(stereo_pairs)}
Scalebars created: {len(created_scalebars)}

Next steps:
1. Check the Reference pane in Metashape
2. Verify that estimated distances appear in the "View Estimated" column
3. Manually export the Reference data to a text file for processing

The scalebars are now ready for manual export and analysis."""
        
        print("\n" + "="*50)
        print("SCALEBAR CREATION COMPLETE")
        print("="*50)
        print(result_message)
        
        Metashape.app.messageBox(result_message)
        
        return len(created_scalebars)
        
    except Exception as e:
        error_message = f"Error creating scalebars: {str(e)}"
        print(error_message)
        Metashape.app.messageBox(error_message)
        return None


def main():
    """Main function to run the scalebar creation script."""
    print("Starting stereo scalebar creation...")
    
    if not Metashape.app.document:
        Metashape.app.messageBox("No document is open. Please open a Metashape project first.")
        return
    
    scalebars_created = create_stereo_scalebars()
    
    if scalebars_created:
        print(f"\nScalebar creation completed!")
        print(f"Created {scalebars_created} scalebars")
        print("Next: manually export Reference data for analysis")
    else:
        print("\nScalebar creation failed.")


if __name__ == "__main__":
    main()
