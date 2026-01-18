import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw
import shutil


class COCOLabelReviewer:
    def __init__(self, root):
        self.root = root
        self.root.title("COCO Label Reviewer")
        self.root.geometry("1200x800")
        
        self.coco_data = None
        self.coco_path = None
        self.images_dir = None
        self.categories = []
        self.selected_category = None
        self.cropped_instances = []
        self.current_index = 0
        self.rejected_annotations = []
        
        self.current_image = None
        self.photo_image = None
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.canvas_image_id = None
        
        self.accepted_count = 0
        self.rejected_count = 0
        
        self.current_page = 1
        
        self.control_frame = None
        self.canvas_frame = None
        self.canvas = None
        self.status_frame = None
        self.progress_label = None
        self.stats_label = None
        self.filename_label = None
        self.zoom_label = None
        
        self.setup_ui()
        self.show_page_1()
    
    def setup_ui(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
    
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_page_1(self):
        self.clear_content()
        self.current_page = 1
        
        title = ttk.Label(self.content_frame, text="COCO Label Reviewer", 
                         font=('Arial', 24, 'bold'))
        title.pack(pady=30)
        
        instructions = ttk.Label(self.content_frame, 
                                text="Step 1: Load your COCO annotation file and images directory",
                                font=('Arial', 12))
        instructions.pack(pady=10)
        
        json_frame = ttk.Frame(self.content_frame)
        json_frame.pack(pady=20)
        
        ttk.Button(json_frame, text="Select COCO JSON File", 
                  command=self.select_coco_json, width=25).pack(side=tk.LEFT, padx=5)
        
        self.json_label = ttk.Label(json_frame, text="No file selected", 
                                   foreground='gray')
        self.json_label.pack(side=tk.LEFT, padx=10)
        
        dir_frame = ttk.Frame(self.content_frame)
        dir_frame.pack(pady=20)
        
        ttk.Button(dir_frame, text="Select Images Directory", 
                  command=self.select_images_dir, width=25).pack(side=tk.LEFT, padx=5)
        
        self.dir_label = ttk.Label(dir_frame, text="No directory selected", 
                                  foreground='gray')
        self.dir_label.pack(side=tk.LEFT, padx=10)
        
        self.status_label = ttk.Label(self.content_frame, text="", 
                                     font=('Arial', 10), foreground='blue')
        self.status_label.pack(pady=20)
        
        self.next_button = ttk.Button(self.content_frame, text="Next →", 
                                     command=self.go_to_page_2, state='disabled')
        self.next_button.pack(pady=30)
    
    def select_coco_json(self):
        filepath = filedialog.askopenfilename(
            title="Select COCO JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'r') as f:
                self.coco_data = json.load(f)
            
            self.coco_path = Path(filepath)
            self.categories = self.coco_data.get('categories', [])
            
            self.json_label.config(text=f"{self.coco_path.name} ({len(self.categories)} categories)", 
                                  foreground='green')
            self.status_label.config(text=f"✓ Loaded {len(self.coco_data.get('images', []))} images, "
                                         f"{len(self.coco_data.get('annotations', []))} annotations")
            
            self.check_ready_for_next()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load COCO JSON:\n{str(e)}")
    
    def select_images_dir(self):
        dirpath = filedialog.askdirectory(title="Select Images Directory")
        
        if not dirpath:
            return
        
        self.images_dir = Path(dirpath)
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files = [f for f in self.images_dir.iterdir() 
                      if f.is_file() and f.suffix.lower() in image_extensions]
        
        self.dir_label.config(text=f"{self.images_dir.name} ({len(image_files)} images)", 
                             foreground='green')
        
        self.check_ready_for_next()
    
    def check_ready_for_next(self):
        if self.coco_data and self.images_dir:
            self.next_button.config(state='normal')
    
    def go_to_page_2(self):
        self.show_page_2()
    
    def show_page_2(self):
        self.clear_content()
        self.current_page = 2
        
        title = ttk.Label(self.content_frame, text="Select Category to Review", 
                         font=('Arial', 20, 'bold'))
        title.pack(pady=20)
        
        ttk.Button(self.content_frame, text="← Back", 
                  command=self.show_page_1).pack(anchor='w', padx=20)
        
        list_frame = ttk.Frame(self.content_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.category_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                          font=('Arial', 12), height=20)
        self.category_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.category_listbox.yview)
        
        annotations = self.coco_data.get('annotations', [])
        category_counts = {}
        for ann in annotations:
            cat_id = ann['category_id']
            category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
        
        for cat in self.categories:
            count = category_counts.get(cat['id'], 0)
            self.category_listbox.insert(tk.END, 
                                        f"{cat['name']} ({count} instances)")
        
        ttk.Button(self.content_frame, text="Process Selected Category", 
                  command=self.process_category).pack(pady=20)
        
        self.process_status = ttk.Label(self.content_frame, text="", 
                                       foreground='blue')
        self.process_status.pack(pady=10)
    
    def process_category(self):
        selection = self.category_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a category first")
            return
        
        idx = selection[0]
        self.selected_category = self.categories[idx]
        
        self.process_status.config(text=f"Processing {self.selected_category['name']}...")
        self.root.update()
        
        category_id = self.selected_category['id']
        annotations = [ann for ann in self.coco_data.get('annotations', [])
                      if ann['category_id'] == category_id]
        
        output_dir = Path('output') / self.selected_category['name']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.cropped_instances = []
        images_dict = {img['id']: img for img in self.coco_data.get('images', [])}
        
        for ann in annotations:
            image_info = images_dict.get(ann['image_id'])
            if not image_info:
                continue
            
            image_path = self.images_dir / image_info['file_name']
            if not image_path.exists():
                continue
            
            try:
                img = Image.open(image_path)
                bbox = ann['bbox']
                x, y, w, h = bbox
                
                padding = 10
                x1 = max(0, int(x - padding))
                y1 = max(0, int(y - padding))
                x2 = min(img.width, int(x + w + padding))
                y2 = min(img.height, int(y + h + padding))
                
                cropped = img.crop((x1, y1, x2, y2))
                
                crop_filename = f"{ann['id']}_{image_info['file_name']}"
                crop_path = output_dir / crop_filename
                cropped.save(crop_path)
                
                self.cropped_instances.append({
                    'path': crop_path,
                    'annotation': ann,
                    'image_info': image_info,
                    'original_image': image_path
                })
                
            except Exception as e:
                print(f"Error processing annotation {ann['id']}: {e}")
        
        self.process_status.config(
            text=f"✓ Processed {len(self.cropped_instances)} instances. Click 'Start Review' to begin.",
            foreground='green'
        )
        
        ttk.Button(self.content_frame, text="Start Review →", 
                  command=self.show_page_3).pack(pady=20)
    
    def show_page_3(self):
        if not self.cropped_instances:
            messagebox.showwarning("Warning", "No instances to review")
            return
        
        self.clear_content()
        self.current_page = 3
        self.current_index = 0
        self.accepted_count = 0
        self.rejected_count = 0
        self.rejected_annotations = []
        
        self.setup_review_ui()
        self.bind_review_events()
        self.load_current_instance()
    
    def setup_review_ui(self):
        self.control_frame = ttk.Frame(self.content_frame)
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        cat_label = ttk.Label(self.control_frame, 
                             text=f"Reviewing: {self.selected_category['name']}",
                             font=('Arial', 12, 'bold'))
        cat_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(self.control_frame, text="Zoom:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Button(self.control_frame, text="-", width=3, 
                  command=self.zoom_out).pack(side=tk.LEFT)
        self.zoom_label = ttk.Label(self.control_frame, text="100%", width=6)
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="+", width=3, 
                  command=self.zoom_in).pack(side=tk.LEFT)
        ttk.Button(self.control_frame, text="Fit", width=4, 
                  command=self.fit_to_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="100%", width=5, 
                  command=self.reset_zoom).pack(side=tk.LEFT)
        
        self.canvas_frame = ttk.Frame(self.content_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg='#2b2b2b', 
                               highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.status_frame = ttk.Frame(self.content_frame)
        self.status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_label = ttk.Label(self.status_frame, text="")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        
        self.stats_label = ttk.Label(self.status_frame, text="Accepted: 0 | Rejected: 0")
        self.stats_label.pack(side=tk.LEFT, padx=20)
        
        self.filename_label = ttk.Label(self.status_frame, text="")
        self.filename_label.pack(side=tk.RIGHT, padx=5)
        
        self.instructions_frame = ttk.Frame(self.content_frame)
        self.instructions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        instructions = "Enter: Accept | Backspace: Reject | Arrow Keys: Navigate | Mouse Wheel: Zoom | Drag: Pan | Esc: Finish"
        ttk.Label(self.instructions_frame, text=instructions, 
                 foreground='gray').pack()
    
    def bind_review_events(self):
        self.root.bind('<Return>', self.accept_instance)
        self.root.bind('<BackSpace>', self.reject_instance)
        self.root.bind('<Left>', self.prev_instance)
        self.root.bind('<Right>', self.next_instance)
        self.root.bind('<Up>', self.prev_instance)
        self.root.bind('<Down>', self.next_instance)
        self.root.bind('<Escape>', self.finish_review)
        
        self.canvas.bind('<ButtonPress-1>', self.start_pan)
        self.canvas.bind('<B1-Motion>', self.do_pan)
        self.canvas.bind('<ButtonRelease-1>', self.end_pan)
        
        self.canvas.bind('<MouseWheel>', self.mouse_wheel_zoom)
        self.canvas.bind('<Button-4>', self.mouse_wheel_zoom)
        self.canvas.bind('<Button-5>', self.mouse_wheel_zoom)
        
        self.canvas.bind('<Configure>', self.on_canvas_resize)
    
    def load_current_instance(self):
        if self.current_index >= len(self.cropped_instances):
            self.finish_review()
            return
        
        instance = self.cropped_instances[self.current_index]
        
        try:
            self.current_image = Image.open(instance['path'])
            self.fit_to_window()
            self.update_status()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image:\n{str(e)}")
            self.next_instance_internal()
    
    def display_image(self):
        if self.current_image is None:
            return
        
        new_width = int(self.current_image.width * self.zoom_level)
        new_height = int(self.current_image.height * self.zoom_level)
        
        if new_width < 1 or new_height < 1:
            return
        
        resized = self.current_image.resize((new_width, new_height), 
                                           Image.Resampling.LANCZOS)
        self.photo_image = ImageTk.PhotoImage(resized)
        
        self.canvas.delete("all")
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if new_width < canvas_width:
            x = canvas_width // 2
        else:
            x = canvas_width // 2 + self.image_offset_x
        
        if new_height < canvas_height:
            y = canvas_height // 2
        else:
            y = canvas_height // 2 + self.image_offset_y
        
        self.canvas_image_id = self.canvas.create_image(
            x, y, image=self.photo_image, anchor=tk.CENTER
        )
        
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
    
    def fit_to_window(self, event=None):
        if self.current_image is None:
            return
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, self.fit_to_window)
            return
        
        width_ratio = canvas_width / self.current_image.width
        height_ratio = canvas_height / self.current_image.height
        self.zoom_level = min(width_ratio, height_ratio) * 0.95
        
        self.image_offset_x = 0
        self.image_offset_y = 0
        
        self.display_image()
    
    def reset_zoom(self):
        self.zoom_level = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.display_image()
    
    def zoom_in(self):
        self.zoom_level = min(self.zoom_level * 1.25, self.max_zoom)
        self.display_image()
    
    def zoom_out(self):
        self.zoom_level = max(self.zoom_level / 1.25, self.min_zoom)
        self.display_image()
    
    def mouse_wheel_zoom(self, event):
        if event.num == 5 or event.delta < 0:
            self.zoom_level = max(self.zoom_level / 1.1, self.min_zoom)
        else:
            self.zoom_level = min(self.zoom_level * 1.1, self.max_zoom)
        self.display_image()
    
    def start_pan(self, event):
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.config(cursor='fleur')
    
    def do_pan(self, event):
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        self.image_offset_x += dx
        self.image_offset_y += dy
        
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        
        self.display_image()
    
    def end_pan(self, event):
        self.canvas.config(cursor='')
    
    def on_canvas_resize(self, event):
        if self.current_image is not None:
            self.display_image()
    
    def accept_instance(self, event=None):
        if self.current_index >= len(self.cropped_instances):
            return
        
        self.accepted_count += 1
        self.next_instance_internal()
    
    def reject_instance(self, event=None):
        if self.current_index >= len(self.cropped_instances):
            return
        
        instance = self.cropped_instances[self.current_index]
        self.rejected_annotations.append(instance['annotation'])
        self.rejected_count += 1
        self.next_instance_internal()
    
    def next_instance_internal(self):
        self.current_index += 1
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.load_current_instance()
    
    def next_instance(self, event=None):
        if self.current_index < len(self.cropped_instances) - 1:
            self.current_index += 1
            self.image_offset_x = 0
            self.image_offset_y = 0
            self.load_current_instance()
    
    def prev_instance(self, event=None):
        if self.current_index > 0:
            self.current_index -= 1
            self.image_offset_x = 0
            self.image_offset_y = 0
            self.load_current_instance()
    
    def update_status(self):
        total = len(self.cropped_instances)
        self.progress_label.config(
            text=f"Instance {self.current_index + 1} of {total}"
        )
        
        instance = self.cropped_instances[self.current_index]
        self.filename_label.config(text=instance['path'].name)
        
        self.stats_label.config(
            text=f"Accepted: {self.accepted_count} | Rejected: {self.rejected_count}"
        )
    
    def finish_review(self, event=None):
        self.root.unbind('<Return>')
        self.root.unbind('<BackSpace>')
        self.root.unbind('<Left>')
        self.root.unbind('<Right>')
        self.root.unbind('<Up>')
        self.root.unbind('<Down>')
        self.root.unbind('<Escape>')
        
        if self.rejected_annotations:
            output_json = Path('output') / f'rejected_{self.selected_category["name"]}.json'
            
            rejected_data = {
                'images': [],
                'annotations': self.rejected_annotations,
                'categories': [self.selected_category]
            }
            
            image_ids = set(ann['image_id'] for ann in self.rejected_annotations)
            images_dict = {img['id']: img for img in self.coco_data.get('images', [])}
            rejected_data['images'] = [images_dict[img_id] for img_id in image_ids 
                                      if img_id in images_dict]
            
            with open(output_json, 'w') as f:
                json.dump(rejected_data, f, indent=2)
            
            result_msg = (f"Review Complete!\n\n"
                         f"Accepted: {self.accepted_count}\n"
                         f"Rejected: {self.rejected_count}\n\n"
                         f"Rejected annotations saved to:\n{output_json}")
        else:
            result_msg = (f"Review Complete!\n\n"
                         f"Accepted: {self.accepted_count}\n"
                         f"Rejected: {self.rejected_count}\n\n"
                         f"No annotations were rejected.")
        
        messagebox.showinfo("Review Complete", result_msg)
        
        self.show_page_2()


def main():
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("Pillow is required. Install with: pip install Pillow")
        sys.exit(1)
    
    root = tk.Tk()
    
    style = ttk.Style()
    style.theme_use('clam')
    
    app = COCOLabelReviewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()