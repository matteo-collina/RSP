import Metashape

def process_metashape_script(distance_value, optimize_cameras, clean_scalebars, threshold_value):
    # Get the active chunk
    chunk = Metashape.app.document.chunk

    # Get all regular cameras in the chunk
    cameras = [camera for camera in chunk.cameras if camera.type == Metashape.Camera.Type.Regular]

    deleted_scalebars_count = 0

    # Check if there are any cameras
    if cameras:
        # Loop through each camera
        for camera1 in cameras:
            for camera2 in cameras:
                # Split the camera labels into parts
                parts1 = camera1.label.split("_")
                parts2 = camera2.label.split("_")
                
                # Ensure the labels have enough parts to process
                if len(parts1) >= 3 and len(parts2) >= 3:
                    # Extract the prefix, side, and number
                    prefix1 = "_".join(parts1[:-2])
                    prefix2 = "_".join(parts2[:-2])
                    side1 = parts1[-2]
                    side2 = parts2[-2]
                    num1 = parts1[-1]
                    num2 = parts2[-1]
                    
                    # Check if prefixes and numbers match and sides are "left" and "right"
                    if prefix1 == prefix2 and num1 == num2 and side1 == "left" and side2 == "right":
                        # Add scalebar with the provided distance
                        scalebar = chunk.addScalebar(camera1, camera2)
                        scalebar.reference.distance = distance_value
                
        # Update the chunk to reflect the changes
        chunk.updateTransform()
        
        # Count the total number of scalebars before cleaning
        total_scalebars_count = len(chunk.scalebars)
        
        # Clean scalebars based on threshold value if requested
        if clean_scalebars:
            scalebars_to_delete = []
            for scalebar in chunk.scalebars:
                if scalebar.error > threshold_value:
                    scalebars_to_delete.append(scalebar)
            
            deleted_scalebars_count = len(scalebars_to_delete)
            for scalebar in scalebars_to_delete:
                chunk.removeScalebar(scalebar)
        
        # Optimize cameras if requested
        if optimize_cameras:
            chunk.optimizeCameras()

        # Calculate the average error of the remaining scalebars
        total_error = sum(scalebar.error for scalebar in chunk.scalebars)
        average_error = total_error / len(chunk.scalebars) if chunk.scalebars else 0
        
        #Prepare the summary message
        summary_message = (
            f"Total number of scalebars found: {total_scalebars_count}\n"
            f"Number of scalebars deleted: {deleted_scalebars_count}\n"
            f"Average error of remaining scalebars: {average_error:.4f} meters"
        )
        
        Metashape.app.messageBox(summary_message)
    else:
        print("No matching cameras found in the chunk.")

def main():
    # Ask user for distance value
    distance_value = Metashape.app.getFloat("Enter distance for scalebars (m):", 1)
    
    # Ask user whether to optimize cameras
    optimize_cameras = Metashape.app.getBool("Do you want to optimize cameras after alignment?")
    
    # Ask user whether to clean scalebars
    clean_scalebars = Metashape.app.getBool("Do you want to clean scalebars?")
    
    # If cleaning is selected, get the threshold value
    if clean_scalebars:
        threshold_value = Metashape.app.getFloat("Enter error threshold for scalebars (m):", 0.01)
    else:
        threshold_value = 15000.0
    
    # Call the Metashape processing function with user inputs
    process_metashape_script(distance_value, optimize_cameras, clean_scalebars, threshold_value)

if __name__ == "__main__":
    main()
