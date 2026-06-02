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
        """Scans ui/ folder for all files ending in _panel.py"""
        mapping = {}
        # This looks for all files like ui/control_panel.py, ui/graphs_panel.py, etc.
        ui_files = glob.glob(os.path.join("ui", "*_panel.py"))
        
        for filepath in ui_files:
            filename = os.path.basename(filepath).replace(".py", "")
            module_name = f"ui.{filename}"
            
            # Dynamically import the module
            module = importlib.import_module(module_name)
            
            # Extract the class name (e.g., control_panel.py -> ControlPanelMixin)
            class_name = "".join([part.capitalize() for part in filename.split("_")]) + "Mixin"
            mixin_class = getattr(module, class_name)
            
            # Generate the build method name
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