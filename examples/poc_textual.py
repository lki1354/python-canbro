from textual.app import App, ComposeResult
from textual.widgets import Input, Label
from textual import events
from textual.reactive import reactive

class Name(Label):
    who = reactive("name")  

class EnterInput(Input):
    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self.emit(events.Change(self, self.value))

class WatchApp(App):
    CSS_PATH = "refresh02.tcss"

    def compose(self) -> ComposeResult:
        yield EnterInput(placeholder="Enter your name")
        yield Name()

    def on_change(self, event: events.Change) -> None:
        self.query_one(Name).who = event.value

if __name__ == "__main__":
    app = WatchApp()
    app.run()