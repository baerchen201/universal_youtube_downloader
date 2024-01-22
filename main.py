import socketserver
import threading
from http.server import BaseHTTPRequestHandler


class YoutubeDownloadHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except ConnectionAbortedError:
            pass
        except BaseException as e:
            try:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(
                    f"The server experienced an unexpected error while processing your request.\nPlease report this on "
                    f"our GitHub issues page and try again later.\n"
                    f"https://github.com/baerchen201/universal_youtube_downloader/issues/new\n"
                    f"{type(e).__name__}: {str(e)}".encode()
                )
            except:
                pass

    def do_GET(self):
        pass


if __name__ == "__main__":
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 8081), YoutubeDownloadHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    try:
        while 1:
            server_thread.join(0.5)
    except KeyboardInterrupt:
        print("Shutting down server...")
        server.shutdown()
        server_thread.join()
    print("Server closed")
