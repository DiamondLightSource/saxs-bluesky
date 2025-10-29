import time
from datetime import datetime
from tkinter import Text, Tk, ttk

from saxs_bluesky.logging.bluesky_messenger import MessageUnpacker, RabbitMQMessenger


class BlueskyLogPanel:
    def __init__(
        self,
        start: bool = True,
        update_interval=0.025,
        rabbitmq_messenger: RabbitMQMessenger | None = None,
        window: Tk | None = None,
        **kwargs,
    ):
        """A simple log panel to display bluesky messages from RabbitMQ."""

        self.update_interval = update_interval  # seconds
        self.run = True
        self.last_message = ""
        self.color = "red"

        ################# GUI SETUP #################

        self.window = window if window is not None else Tk()
        self.window.title("Bluesky Log Panel")

        self.window.wm_resizable(True, True)
        self.window.minsize(1400, 400)
        self.style = ttk.Style(self.window)

        if rabbitmq_messenger is not None:
            self.messenger = rabbitmq_messenger
        elif len(kwargs) > 0:
            self.messenger = RabbitMQMessenger(**kwargs)

        self.logs = Text(self.window, state="disabled", font=("Helvetica", 10))
        self.logs.pack(fill="both", expand=True, side="left", anchor="w")

        self.logs.tag_config("warning", background="yellow", foreground="red")
        self.logs.tag_config("error", background="red", foreground="white")
        self.logs.tag_config("log", background="white", foreground="black")

        self.scrollbar = ttk.Scrollbar(
            self.window, orient="vertical", command=self.logs.yview
        )
        self.scrollbar.pack(fill="y", side="right")
        self.logs.configure(yscrollcommand=self.scrollbar.set)

        self.window.bind("<Destroy>", self.on_destroy)

        if start:
            self.run_loop()

    def run_loop(self):
        self.window.update_idletasks()
        self.window.update()
        self.run_listener()

    def log_message(self, message: str, timestamp: bool = True):
        if timestamp:
            timenow = datetime.now()
            timestamp = timenow.strftime("%Y-%m-%d %H:%M:%S")  # type: ignore
            log_entry = f"[{timestamp}] {message}\n"
        else:
            log_entry = f"{message}\n"

        self.logs.config(state="normal")
        self.logs.insert("end", log_entry, "log")
        self.logs.config(state="disabled")  # stops user editing

    def run_listener(self):
        while self.run:
            if not self.messenger.scan_listener.messages:
                pass
            else:
                recieved_message = self.messenger.get_message()

                if recieved_message != self.last_message:
                    self.last_message = recieved_message

                    messages = MessageUnpacker.unpack_dict(recieved_message)

                    for message in messages:
                        self.log_message(message)
                        self.logs.see("end")

                self.log_message("--------MESSAGE END----------", timestamp=False)

            time.sleep(self.update_interval)
            self.window.update_idletasks()
            self.window.update()

    def on_destroy(self, event):
        self.run = False
        print("Shutting down messenger...")
        self.messenger.disconnect()


if __name__ == "__main__":
    BlueskyLogPanel(beamline="i22")
