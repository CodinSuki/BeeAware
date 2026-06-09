import customtkinter as ctk
import sys
import importlib
import os
import glob

class PreviewApp(ctk.CTk):
    def __init__(self, component_name):
        super().__init__()
        self.title(f"Preview: {component_name}")
        self.geometry("900x300")
        
        self.ai_status = "System Ready"
        self.models_ready = True
        
        # Automatically discover UI components
        self.components = self.discover_components()
        
        self.load_component(component_name)

    def discover_components(self):
        """Scans ui/ folder for ALL .py files."""
        mapping = {}
        # Changed from "*_panel.py" to "*.py"
        ui_files = glob.glob(os.path.join("ui", "*.py"))
        
        for filepath in ui_files:
            filename = os.path.basename(filepath).replace(".py", "")
            
            # Skip the __init__.py file
            if filename == "__init__":
                continue
                
            module_name = f"ui.{filename}"
            module = importlib.import_module(module_name)
            
            # Update the class naming logic
            # This handles both "control_panel" -> "ControlPanelMixin" 
            # and "correction" -> "CorrectionMixin"
            parts = filename.split("_")
            class_name = "".join([part.capitalize() for part in parts]) + "Mixin"
            
            # Safely get the class if it exists
            if hasattr(module, class_name):
                mixin_class = getattr(module, class_name)
                # This assumes your build methods follow build_{filename}
                method_name = f"build_{filename}"
                mapping[filename] = (mixin_class, method_name)
        
        return mapping

    def load_component(self, name):
        if name not in self.components:
            print(f"Error: '{name}' not found. Available: {list(self.components.keys())}")
            return

        mixin_class, method_name = self.components[name]

        class ComponentHost(ctk.CTkFrame, mixin_class):
            def __init__(self, master, app):
                super().__init__(master, fg_color="transparent")
                self.parent_app = app
                self.ai_status = app.ai_status
                self.models_ready = app.models_ready
                getattr(self, method_name)()

            # Proxy methods to prevent crashes
            def __getattr__(self, name):
                # This catches any missing command methods automatically!
                return lambda: print(f"Method '{name}' called but not implemented.")
        
        panel = ComponentHost(self, self)
        panel.pack(fill="both", expand=True, padx=20, pady=20)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "control_panel"
    app = PreviewApp(target)
    app.mainloop()