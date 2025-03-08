from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window

class TestKeyboardApp(App):
    def build(self):
        layout = BoxLayout()
        self.input_text = TextInput(hint_text="Tap here", size_hint=(1, 0.7))
        layout.add_widget(self.input_text)

        # Debugging focus
        self.input_text.bind(focus=self.debug_focus)

        return layout

    def debug_focus(self, instance, value):
        if value:
            print("TextInput focused - expecting keyboard to work.")
        else:
            print("TextInput lost focus.")

if __name__ == "__main__":
    TestKeyboardApp().run()
