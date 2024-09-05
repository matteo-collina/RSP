import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk 
import random 
import shutil
import cv2
import numpy as np
import webbrowser
from sceneRadianceCLAHE import RecoverCLAHE

class ImageProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Processor")

        # Set the icon
        icon_path = os.path.join(os.path.dirname(__file__), "app_icon.png")  # Adjust the filename as needed
        if os.path.isfile(icon_path):
            pil_icon = Image.open(icon_path)
            self.icon_image = ImageTk.PhotoImage(pil_icon)  # Keep a reference to the image
            self.root.tk.call('wm', 'iconphoto', self.root._w, self.icon_image)

        # Create the menu bar
        self.menu_bar = tk.Menu(root)
        root.config(menu=self.menu_bar)

        # Create the Menu
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="Documentation", command=self.show_documentation)
        self.help_menu.add_command(label="About", command=self.show_about_info)
        self.tools_menu.add_command(label="GoPro QR Code", command=self.show_gropro_qr)

        # Load logo images
        logo_path = os.path.join(os.path.dirname(__file__), "university_logo.png")
        if not os.path.isfile(logo_path):
            print(f"Error: The file {logo_path} does not exist.")
        else:
            self.logo1 = tk.PhotoImage(file=logo_path)

        # Create a frame for the logos
        logo_frame = tk.Frame(root)
        logo_frame.pack(side=tk.TOP, fill=tk.X, pady=10)

        # Add logo images to labels
        if hasattr(self, 'logo1'):
            self.logo_label1 = tk.Label(logo_frame, image=self.logo1)
            self.logo_label1.pack(side=tk.TOP, padx=10)
        else:
            print("Error: Image could not be loaded.")

        # Create the main frame
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create the frame for the left side
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.paths = {"center": "", "left": "", "right": ""}
        self.prefix1 = tk.StringVar()
        self.prefix2 = tk.StringVar()
        self.prefix3 = tk.StringVar()

        # Create and place the prefix entry fields
        prefix_frame1 = tk.Frame(left_frame)
        prefix_frame1.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(prefix_frame1, text="Prefix 1:").pack(side=tk.LEFT)
        tk.Entry(prefix_frame1, textvariable=self.prefix1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        prefix_frame2 = tk.Frame(left_frame)
        prefix_frame2.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(prefix_frame2, text="Prefix 2:").pack(side=tk.LEFT)
        tk.Entry(prefix_frame2, textvariable=self.prefix2).pack(side=tk.LEFT, fill=tk.X, expand=True)

        prefix_frame3 = tk.Frame(left_frame)
        prefix_frame3.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(prefix_frame3, text="Prefix 3:").pack(side=tk.LEFT)
        tk.Entry(prefix_frame3, textvariable=self.prefix3).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Create directory selection 
        for prefix in self.paths:
            select_frame = tk.Frame(left_frame)
            select_frame.pack(fill=tk.X, padx=10, pady=5)

            tk.Label(select_frame, text=f"Select {prefix} directory:").pack(side=tk.TOP, anchor=tk.W)

            path_label_frame = tk.Frame(select_frame)
            path_label_frame.pack(fill=tk.X)

            path_label = tk.Label(path_label_frame, text="No directory selected", width=50)
            path_label.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
            setattr(self, f"{prefix}_path_label", path_label)

            button_frame = tk.Frame(select_frame)
            button_frame.pack(fill=tk.X)

            browse_button = tk.Button(button_frame, text="Browse", command=lambda p=prefix: self.browse_directory(p), width=10, height=1)
            browse_button.pack(side=tk.LEFT, padx=(0, 10))
            
            clear_button = tk.Button(button_frame, text="Clear", command=lambda p=prefix: self.clear_directory(p), width=10, height=1)
            clear_button.pack(side=tk.LEFT)

        # Create a general button to clear all directories
        clear_all_button = tk.Button(left_frame, text="Clear All Directories", command=self.clear_all_directories, width=15, height=1)
        clear_all_button.pack(pady=10, fill=tk.X, padx=10)

        # Add the image enhancement checkbox
        self.enhancement_var = tk.BooleanVar()
        enhancement_checkbox = tk.Checkbutton(left_frame, text="Image Enhancement", variable=self.enhancement_var, command=self.toggle_enhancement_section)
        enhancement_checkbox.pack(pady=10)

        # Create the run button
        run_button = tk.Button(left_frame, text="Process Images", command=self.process_images, width=15, height=2, font=("Arial", 14, "bold"))
        run_button.pack(pady=20, fill=tk.X, padx=10)

        # Create the progress bar and percentage label
        self.progress_var = tk.DoubleVar()
        self.progress_label = tk.Label(left_frame, text="0%")
        self.progress_label.pack(pady=(20, 0))
        self.progress_bar = ttk.Progressbar(left_frame, orient="horizontal", length=300, mode="determinate", variable=self.progress_var)
        self.progress_bar.pack(pady=10, fill=tk.X, padx=10)

        # Create a frame for the enhancement section
        self.enhancement_frame = tk.Frame(main_frame, width=700, height=400)
        self.enhancement_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            # To ensure the frame maintains the size, use the minsize method
        self.enhancement_frame.update_idletasks()  # Ensure the frame is updated before setting minsize
        self.enhancement_frame.pack_propagate(False)  # Prevent the frame from resizing to fit its content
        self.enhancement_frame.pack_forget()  # Hide the frame initially

        # Create a vertical frame for the preview and button
        preview_button_frame = tk.Frame(self.enhancement_frame, width=80)
        preview_button_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add an image previewer to the vertical frame
        self.image_preview = tk.Label(preview_button_frame, bg="gray", width=80, height=10)  # Adjust width and height
        self.image_preview.pack(side=tk.TOP, padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Add the test button below the image preview
        test_button = tk.Button(preview_button_frame, text="Test Image Enhancment", command=self.test_image_enhancement)
        test_button.pack(side=tk.BOTTOM, padx=20, pady=20)

        # Add a temporary folder path
        self.temp_folder = "TempImages"
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)

    def browse_directory(self, prefix):
        directory = filedialog.askdirectory()
        if directory:
            self.paths[prefix] = directory
            getattr(self, f"{prefix}_path_label").config(text=directory)

    def clear_directory(self, prefix):
        self.paths[prefix] = ""
        getattr(self, f"{prefix}_path_label").config(text="No directory selected")

    def clear_all_directories(self):
        for prefix in self.paths:
            self.clear_directory(prefix)

    def process_images(self):
        try:
            prefix1 = self.prefix1.get()
            prefix2 = self.prefix2.get()
            prefix3 = self.prefix3.get()
            total_files = sum(len(os.listdir(path)) for path in self.paths.values() if path)
            
            # Initialize progress bar for renaming
            self.progress_var.set(0)
            if self.enhancement_var.get():
                self.progress_bar["maximum"] = total_files + total_files
            else:
                self.progress_bar["maximum"] = total_files 

            current_file = 0

            renamed_images = []  # To keep track of renamed images for enhancement

            for prefix, path in self.paths.items():
                if path:
                    current_file = self.rename_files_in_directory(path, prefix, prefix1, prefix2, prefix3, current_file, renamed_images)

            # If enhancement is enabled, apply enhancement and update progress
            if self.enhancement_var.get():
                self.apply_image_enhancement(renamed_images, current_file)
                self.progress_label.config(text="100%")
                self.progress_bar.update()
            else:
                # Finalize progress bar
                self.progress_var.set(self.progress_bar["maximum"])
                self.progress_label.config(text="100%")
                self.progress_bar.update()

            if self.enhancement_var.get():
                messagebox.showinfo("Success", "All pictures renamed and enhanced successfully.")
            else:
                messagebox.showinfo("Succes", "All pictures renamed successfully.")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def rename_files_in_directory(self, directory, prefix, prefix1, prefix2, prefix3, current_file, renamed_images):
        files = [(filename, os.path.getmtime(os.path.join(directory, filename))) for filename in os.listdir(directory)]
        files.sort(key=lambda x: x[1])  # Sort files by creation time

        counter = 0
        for filename, _ in files:
            file_path = os.path.join(directory, filename)

            if prefix1 and prefix2 and prefix3:
                new_name = f"{prefix1}_{prefix2}_{prefix3}_{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"
            elif prefix1 and prefix2:
                new_name = f"{prefix1}_{prefix2}_{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"
            elif prefix1:
                new_name = f"{prefix1}_{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"
            else:
                new_name = f"{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"

            new_file_path = os.path.join(directory, new_name)

            if os.path.exists(new_file_path):
                counter += 1
                new_name = f"{prefix}_{str(counter).zfill(5)}{os.path.splitext(filename)[1]}"
                new_file_path = os.path.join(directory, new_name)

            os.rename(file_path, new_file_path)
            renamed_images.append(new_file_path)  # Add the renamed image path to the list
            counter += 1
            current_file += 1
            self.progress_var.set(current_file)
            self.progress_label.config(text=f"{int((current_file / self.progress_bar['maximum']) * 100)}%")
            self.progress_bar.update()

        return current_file

    def apply_image_enhancement(self, renamed_images, start_index):
        total_files = len(renamed_images)
        current_progress = start_index
        
        for index, image_path in enumerate(renamed_images):
            img = cv2.imread(image_path)
            if img is not None:
                # Load the image using Pillow to access EXIF data
                pil_image = Image.open(image_path)
                exif_data = pil_image.info.get('exif')

                # Create an "Enhanced" folder in the same directory as the current image
                enhanced_folder = os.path.join(os.path.dirname(image_path), "Enhanced")
                if not os.path.exists(enhanced_folder):
                    os.makedirs(enhanced_folder)

                # Apply CLAHE enhancement
                enhanced_img_clahe = RecoverCLAHE(img)
                temp_name_clahe = os.path.splitext(os.path.basename(image_path))[0] + '.jpg'
                temp_path_clahe = os.path.join(enhanced_folder, temp_name_clahe)
                cv2.imwrite(temp_path_clahe, enhanced_img_clahe)

                # Re-open the enhanced image with Pillow to attach EXIF data
                enhanced_pil_image = Image.open(temp_path_clahe)
                enhanced_pil_image.save(temp_path_clahe, exif=exif_data)
                
                # Update progress
                current_progress += 1
                self.progress_var.set(current_progress)
                self.progress_label.config(text=f"{int((current_progress / self.progress_bar['maximum']) * 100)}%")
                self.progress_bar.update()

        # Ensure progress bar reflects the end of the process
        self.progress_var.set(self.progress_bar["maximum"])
        self.progress_label.config(text="100%")
        self.progress_bar.update()
        
    def show_gropro_qr(self):
        # Create a new top-level window
        about_window = tk.Toplevel(self.root)
        about_window.title("GoPro QR Code")
        about_window.geometry("400x600")
        about_window.tk.call('wm', 'iconphoto', about_window._w, self.icon_image)

        # Load the image
        image_path = os.path.join(os.path.dirname(__file__), "gopro_qr_code.png")  # Adjust the filename as needed
        if not os.path.isfile(image_path):
            print(f"Error: The file {image_path} does not exist.")
            return  # Exit the function if the image file is not found

        pil_image = Image.open(image_path)

        image_width = 250
        image_height = image_width #QR squared format
        pil_image = pil_image.resize((image_width, image_height))
        self.qr_image = ImageTk.PhotoImage(pil_image)  # Keep a reference to avoid garbage collection

        # Create a label to display the image
        image_label = tk.Label(about_window, image=self.qr_image)
        image_label.pack(padx=10, pady=10)

        # Create a text widget for custom content
        text = tk.Text(about_window, wrap=tk.WORD, height=100, width=100, bg=about_window.cget('bg'))
        text.pack(padx=10, pady=10)

        # Insert text with different styles
        text.insert(tk.END, "SETTINGS\n\n", "bold")
        text.insert(tk.END, "White-Balance: ", "bold")
        text.insert(tk.END, "Auto", "normal")
        text.insert(tk.END, "\n\n\n", "normal")
        text.insert(tk.END, "YOU NEED THE LABS FIRMWARE IN ORDER TO USE IT. PLEASE, REFER TO DOCUMENTATION.\n\n", "bold")
        text.insert(tk.END, "PLEASE, REMEMBER TO TURN ON INTERVALOMETER FUNCTION ON THE GOPRO. ", "bold")
        
        # Define different styles
        text.tag_configure("bold", font=("Arial", 10, "bold"))
        text.tag_configure("normal", font=("Arial", 10))
                           
        # Make the text widget read-only
        text.config(state=tk.DISABLED)

        # Add a close button
        close_button = tk.Button(about_window, text="Close", command=about_window.destroy)
        close_button.pack(pady=10)

    def show_about_info(self):
        # Create a new top-level window
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        about_window.geometry("500x400")  # Adjust size as needed
        about_window.tk.call('wm', 'iconphoto', about_window._w, self.icon_image)

        # Create a text widget for custom content
        text = tk.Text(about_window, wrap=tk.WORD, height=100, width=100, bg=about_window.cget('bg'))
        text.pack(padx=10, pady=10)

        # Insert text with different styles
        text.insert(tk.END, "XXX\n", "bold")
        text.insert(tk.END, "A Victoria University of Wellington project\n", "normal")
        text.insert(tk.END, "Developed by Seammetry\n\n", "normal")
        text.insert(tk.END, "CREDITS:\n", "bold")
        text.insert(tk.END, "Software Development: ", "bold")
        text.insert(tk.END, "Matteo Collina\n", "normal")
        text.insert(tk.END, "Testing: ", "bold")
        text.insert(tk.END, "Manon Payne Broadribb, Miriam Pierotti\n", "normal")
        text.insert(tk.END, "Supervision: ", "bold")
        text.insert(tk.END, "Prof. James Bell\n\n", "normal")
        text.insert(tk.END, "Version: 1.0\n", "normal")
        text.insert(tk.END, "Date: September 2024\n", "normal")
        text.insert(tk.END, "Contact: matteo.collina@vuw.ac.nz\n\n\n", "normal")

        # Define different styles
        text.tag_configure("bold", font=("Arial", 10, "bold"))
        text.tag_configure("normal", font=("Arial", 10))
                           
        # Make the text widget read-only
        text.config(state=tk.DISABLED)

        # Add a close button
        close_button = tk.Button(about_window, text="Close", command=about_window.destroy)
        close_button.pack(pady=10)

    def show_documentation(self):
        # URL to open
        url = "https://www.google.com"  # Replace with your actual URL

        # Open the URL in the default web browser
        webbrowser.open(url)    

    def toggle_enhancement_section(self):
        if self.enhancement_var.get():
            self.enhancement_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        else:
            self.enhancement_frame.pack_forget()

    def test_image_enhancement(self):
        left_folder = self.paths.get("left")
        if not left_folder:
            messagebox.showwarning("Warning", "Left folder is not selected.\n Please select a left folder in the main panel.")
            return

        # Ensure the TempImages folder exists
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)

        # Clear the TempImages folder if it already contains files
        for filename in os.listdir(self.temp_folder):
            file_path = os.path.join(self.temp_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # Select a random image from the left folder
        files = [f for f in os.listdir(left_folder) if os.path.isfile(os.path.join(left_folder, f))]
        if not files:
            messagebox.showwarning("Warning", "No images found in the left folder.")
            return

        random_file = random.choice(files)
        random_image_path = os.path.join(left_folder, random_file)
        temp_image_path = os.path.join(self.temp_folder, random_file)

        # Copy the selected image to the temp folder
        shutil.copy(random_image_path, temp_image_path)

        # Apply image enhancement
        img = cv2.imread(temp_image_path)
        if img is not None:
            if self.enhancement_var.get():
                # Apply CLAHE enhancement
                enhanced_img_clahe = RecoverCLAHE(img)
                temp_name_clahe = os.path.splitext(random_file)[0] + '_CLAHE.jpg'
                temp_path_clahe = os.path.join(self.temp_folder, temp_name_clahe)
                cv2.imwrite(temp_path_clahe, enhanced_img_clahe)

                # Display the CLAHE enhanced image
                self.display_image(temp_path_clahe)
            else:
                # Display the original image if enhancement is not checked
                self.display_image(temp_image_path)

        # Schedule the deletion of the TempImages folder after 5 seconds
        self.root.after(5000, self.delete_temp_folder)

    def delete_temp_folder(self):
        # Remove all files in the TempImages folder
        for filename in os.listdir(self.temp_folder):
            file_path = os.path.join(self.temp_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Remove the TempImages folder itself if empty
        if not os.listdir(self.temp_folder):
            os.rmdir(self.temp_folder)

    def display_image(self, image_path):
        img = Image.open(image_path)
        
        # Fixed dimensions for the preview label
        max_width = 600
        max_height = 525

        # Resize image to fit within the max dimensions while maintaining aspect ratio
        img.thumbnail((max_width, max_height), Image.LANCZOS)

        # Convert image to a format suitable for Tkinter
        img_tk = ImageTk.PhotoImage(img)

        # Update the label with the new image
        self.image_preview.config(image=img_tk)
        self.image_preview.image = img_tk  # Keep a reference to avoid garbage collection

        # Debugging sizes
        print(f"Label size: {self.image_preview.winfo_width()}x{self.image_preview.winfo_height()}")
        print(f"Image size: {img.size[0]}x{img.size[1]}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessor(root)
    root.mainloop()
