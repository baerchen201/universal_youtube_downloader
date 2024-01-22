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
                    f"The server experienced an unexpected error while processing your request.\nPlease report this on our GitHub issues page and try again later.\n{type(e).__name__}: {str(e)}".encode()
                )
            except:
                pass

    def do_GET(self):
        pass
