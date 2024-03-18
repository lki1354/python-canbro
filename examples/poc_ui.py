import npyscreen

class SignalForm(npyscreen.Form):
    def create(self):
        self.name = self.add(npyscreen.TitleText, name="Signal Name")
        self.value = self.add(npyscreen.TitleSlider, out_of=100, name="Signal Value")

class SignalApp(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', SignalForm, name="Signal App")

if __name__ == "__main__":
    app = SignalApp()
    app.run()