import re
import socketserver
import threading
from http.server import BaseHTTPRequestHandler

import pytube
import pytube.exceptions


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
        regex = re.match(r"/([A-Za-z0-9-_]{11})/(\d{,2})", self.path)
        if not regex:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f'Bad url formatting, "/<video-id>/<stream-id>'.encode())
            return

        video_id = regex.group(1)
        stream_id = regex.group(2)

        video = pytube.YouTube("/" + video_id)
        _ = None
        streams = None
        try:
            _ = video.title
            streams = video.streams
        except pytube.exceptions.VideoPrivate:
            self.send_response(403)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write("Video is private".encode())
        except pytube.exceptions.VideoRegionBlocked:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write("Video unavailable in the region of the server".encode())
        except pytube.exceptions.VideoUnavailable:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write("Video can not be accessed".encode())
        if not _:
            return
        if not streams:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write("The video did not return any download links".encode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(video.title.encode())


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
