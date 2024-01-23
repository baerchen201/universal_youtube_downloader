import http.client
import math
import re
import socketserver
import threading
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler

import pytube
import pytube.exceptions
import requests
import telebot

import config


class YoutubeDownloadHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except ConnectionAbortedError:
            pass
        except BaseException as e:
            print("".join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)))
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

    def do_GET(self, send_content: bool = True):
        regex = re.match(r"/([A-Za-z0-9-_]{11})/(\d{,2})", self.path)
        if not regex:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if send_content:
                self.wfile.write(f'Bad url formatting, "/<video-id>/<stream-id>'.encode())
            return

        video_id = regex.group(1)
        stream_id = int(regex.group(2))

        video = pytube.YouTube("/" + video_id)
        _ = None
        streams: pytube.StreamQuery | None = None
        try:
            _ = video.title
            streams = video.streams
        except pytube.exceptions.VideoPrivate:
            self.send_response(403)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if send_content:
                self.wfile.write(f"Video is private ({video_id})".encode())
        except pytube.exceptions.VideoRegionBlocked:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if send_content:
                self.wfile.write(f"Video unavailable in the region of the server ({video_id})".encode())
        except pytube.exceptions.VideoUnavailable:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if send_content:
                self.wfile.write(f"Video can not be accessed ({video_id})".encode())
        if not _:
            return
        if not streams:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if send_content:
                self.wfile.write("The video did not return any download links".encode())
            return
        if len(streams) <= stream_id:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if send_content:
                self.wfile.write(
                    f"The requested stream id is out of range, only {len(streams)} streams available".encode()
                )
            return
        else:
            stream: pytube.Stream = streams[stream_id]
            url = stream.url
            head = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            }
            head.update({"Range": self.headers.get("Range")} if "Range" in self.headers else {})
            ggl_conn: http.client.HTTPResponse = urllib.request.urlopen(urllib.request.Request(url, headers=head))
            if ggl_conn.getcode() not in (200, 206):
                self.send_response(502)
                for header in ggl_conn.getheaders():
                    self.send_header(*header)
                self.end_headers()
                if send_content:
                    self.wfile.write("Non-success status code".encode())
                self.send_response(ggl_conn.getcode())
                for header in ggl_conn.getheaders():
                    self.send_header(*header)
                self.end_headers()
                if send_content:
                    self.wfile.write(ggl_conn.read(4096))
                return
            else:
                self.send_response(ggl_conn.getcode())
                for header in ggl_conn.getheaders():
                    if header[0] in ("Content-Type", "Content-Disposition"):
                        continue
                    self.send_header(*header)
                self.send_header("Content-Type", stream.mime_type)
                self.send_header("Content-Disposition", f"attachment;filename={stream.default_filename}")
                self.end_headers()
                while send_content:
                    chunk = ggl_conn.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

    def do_HEAD(self):
        self.do_GET(False)


telegram_bot = telebot.TeleBot(config.TELEGRAM_TOKEN)


@telegram_bot.message_handler()
def handle_message(msg):
    regex = re.fullmatch(r"[\s\S]*(?:/|v=)([A-Za-z0-9-_]{11})[\s\S]*|([A-Za-z0-9-_]{11})", msg.text)
    if not regex:
        telegram_bot.reply_to(msg, "Invalid url")
        return
    video_id = regex.group(1)

    video = pytube.YouTube("/" + video_id)
    _ = None
    streams: pytube.StreamQuery | None = None
    try:
        _ = video.title
        streams = video.streams
    except pytube.exceptions.VideoPrivate:
        telegram_bot.reply_to(msg, f"Video is private ({video_id})")
    except pytube.exceptions.VideoRegionBlocked:
        telegram_bot.reply_to(msg, f"Video unavailable in the region of the server ({video_id})")
    except pytube.exceptions.VideoUnavailable:
        telegram_bot.reply_to(msg, f"Video can not be accessed ({video_id})")
    if not _:
        return

    video_streams, audio_streams = [], []
    stream: pytube.Stream
    for stream in streams:
        if stream.type == "audio":
            audio_streams.append(stream)
        else:
            video_streams.append(stream)

    keyboard = telebot.types.InlineKeyboardMarkup()
    video_streams.sort(key=lambda i: int(i.resolution.split("p")[0]))
    for stream in video_streams:
        btn = telebot.types.InlineKeyboardButton(
            f"{stream.mime_type} {stream.resolution} {stream.abr if stream.abr is not None else str(math.floor(stream.bitrate / 1024)) + 'kbps'}",
            callback_data="/" + video_id + "/" + str(streams.index(stream)),
        )
        keyboard.add(btn)

    telegram_bot.reply_to(msg, "Please select a download option:", reply_markup=keyboard)


@telegram_bot.callback_query_handler(func=lambda call: True)
def callback_query(ctx: telebot.types.CallbackQuery):
    regex = re.match(r"/([A-Za-z0-9-_]{11})/(\d{,2})", ctx.data)
    video_id = regex.group(1)
    stream_id = int(regex.group(2))
    if video_id is None or stream_id is None:
        telegram_bot.edit_message_text(
            "Invalid callback, please try again later", ctx.message.chat.id, ctx.message.id, reply_markup=None
        )
        return

    video = pytube.YouTube("/" + video_id)
    _ = None
    streams: pytube.StreamQuery | None = None
    try:
        _ = video.title
        streams = video.streams
    except pytube.exceptions.VideoPrivate:
        telegram_bot.edit_message_text(f"Video is private ({video_id})", ctx.message.chat.id, ctx.message.id)
    except pytube.exceptions.VideoRegionBlocked:
        telegram_bot.edit_message_text(
            f"Video unavailable in the region of the server ({video_id})", ctx.message.chat.id, ctx.message.id
        )
    except pytube.exceptions.VideoUnavailable:
        telegram_bot.edit_message_text(f"Video can not be accessed ({video_id})", ctx.message.chat.id, ctx.message.id)
    if not _:
        return

    if len(streams) <= stream_id:
        telegram_bot.edit_message_text(
            f"The requested stream id is out of range, only {len(streams)} streams available",
            ctx.message.chat.id,
            ctx.message.id,
        )
        return

    telegram_bot.edit_message_text(
        f"Successfully loaded video {video_id}, sending...", ctx.message.chat.id, ctx.message.id
    )
    stream: pytube.Stream = streams[stream_id]
    url = (
            "http://"
            + requests.get("http://ifconfig.me/ip").text
            + f":8081/{video_id}/{stream_id}/video.{stream.mime_type.split('/')[1]}"
    )
    print(url)
    try:
        getattr(telegram_bot, f"send_{stream.type}")(ctx.message.chat.id, url)
    except BaseException as e:
        telegram_bot.edit_message_text(
            f"The bot was unable to send the video. You can download the video manually:"
            f'\n<a href="{url}">{stream.default_filename}</a>',
            ctx.message.chat.id,
            ctx.message.id,
            parse_mode="HTML",
        )
        print("".join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))


if __name__ == "__main__":
    server = socketserver.ThreadingTCPServer(("0.0.0.0", 8081), YoutubeDownloadHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    telegram_bot_thread = threading.Thread(target=telegram_bot.infinity_polling())
    telegram_bot_thread.start()
    try:
        while 1:
            server_thread.join(0.5)
            telegram_bot_thread.join(0.5)
    except KeyboardInterrupt:
        print("Shutting down server...")
        server.shutdown()
        telegram_bot.stop_polling()
        server_thread.join()
    print("Server closed")
