from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window

class TestKeyboardApp(App):
    def build(self):
        layout = BoxLayout()
        self.input_text = TextInput(hint_text="Tap here", size_hint=(1, 0.2))
        layout.add_widget(self.input_text)
        
        # Bind focus to check if keyboard is requested
        self.input_text.bind(focus=self.on_text_focus)
        
        return layout

    def on_text_focus(self, instance, value):
        """ Check if keyboard is requested when TextInput is focused """
        if value:
            print("Keyboard requested")  # Should print when tapped
            keyboard = Window.request_keyboard(None, instance)
            if keyboard:
                print("Keyboard should appear now!")
            else:
                print("Keyboard request failed!")

if __name__ == "__main__":
    TestKeyboardApp().run()
