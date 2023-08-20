import copy
import json
from typing import Union, List
from urllib.parse import urlencode
import re

from youtubesearchpython.core.constants import *
from youtubesearchpython.core.requests import RequestCore
from youtubesearchpython.core.componenthandler import getValue, getVideoId


CLIENTS = {
    "MWEB": {
        'context': {
            'client': {
                'clientName': 'MWEB',
                'clientVersion': '2.20211109.01.00'
            }
        },
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
    },
    "ANDROID": {
        'context': {
            'client': {
                'clientName': 'ANDROID',
                'clientVersion': '16.20'
            }
        },
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
    },
    "ANDROID_EMBED": {
        'context': {
            'client': {
                'clientName': 'ANDROID',
                'clientVersion': '16.20',
                'clientScreen': 'EMBED'
            }
        },
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
    },
    "TV_EMBED": {
        "context": {
            "client": {
                "clientName": "TVHTML5_SIMPLY_EMBEDDED_PLAYER",
                "clientVersion": "2.0"
            },
            "thirdParty": {
                "embedUrl": "https://www.youtube.com/",
            }
        },
        'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
    }
}


class VideoCore(RequestCore):
    def __init__(self, videoLink: str, componentMode: str, resultMode: int, timeout: int, enableHTML: bool, overridedClient: str = "ANDROID"):
        super().__init__()
        self.timeout = timeout
        self.resultMode = resultMode
        self.componentMode = componentMode
        self.videoLink = videoLink
        self.enableHTML = enableHTML
        self.overridedClient = overridedClient
    
    # We call this when we use only HTML
    def post_request_only_html_processing(self):
        self.__getVideoComponent(self.componentMode)
        self.result = self.__videoComponent

    def post_request_processing(self):
        self.__parseSource()
        self.__getVideoComponent(self.componentMode)
        self.result = self.__videoComponent

    def prepare_innertube_request(self):
        self.url = 'https://www.youtube.com/youtubei/v1/player' + "?" + urlencode({
            'key': searchKey,
            'contentCheckOk': True,
            'racyCheckOk': True,
            "videoId": getVideoId(self.videoLink)
        })
        self.data = copy.deepcopy(CLIENTS[self.overridedClient])

    async def async_create(self):
        self.prepare_innertube_request()
        response = await self.asyncPostRequest()
        self.response = response.text
        if response.status_code == 200:
            self.post_request_processing()
        else:
            raise Exception('ERROR: Invalid status code.')

    def sync_create(self):
        self.prepare_innertube_request()
        response = self.syncPostRequest()
        self.response = response.text
        if response.status_code == 200:
            self.post_request_processing()
        else:
            raise Exception('ERROR: Invalid status code.')

    def prepare_html_request(self):
        self.url = 'https://www.youtube.com/youtubei/v1/player' + "?" + urlencode({
            'key': searchKey,
            'contentCheckOk': True,
            'racyCheckOk': True,
            "videoId": getVideoId(self.videoLink)
        })
        self.data = CLIENTS["MWEB"]

    def prepare_next_request(self):
        self.url = 'https://www.youtube.com/youtubei/v1/next' + "?" + urlencode({
            'key': searchKey
        })
        self.data = copy.deepcopy(requestPayload)
        '''self.data['autonavState'] = "STATE_OFF"
        self.data['captionsRequested'] = False
        self.data['contentCheckOk'] = False
        self.data['playbackContext'] = {'vis' : 0, 'lactMilliseconds' : "-1"}
        self.data['racyCheckOk'] = False'''
        self.data['videoId'] = getVideoId(self.videoLink)
        

    def sync_html_create(self):
        self.prepare_html_request()
        response = self.syncPostRequest()
        self.HTMLresponseSource = response.json()

    async def async_html_create(self):
        self.prepare_html_request()
        response = await self.asyncPostRequest()
        self.HTMLresponseSource = response.json()

    def sync_next_create(self):
        self.prepare_next_request()
        response = self.syncPostRequest()        
        self.nextResponseSource = response.json()

    async def async_next_create(self):
        self.prepare_next_request()
        response = await self.syncPostRequest()        
        self.nextResponseSource = response.json()

    def __parseSource(self) -> None:
        try:
            self.responseSource = json.loads(self.response)
        except Exception as e:
            raise Exception('ERROR: Could not parse YouTube response.')

    def __result(self, mode: int) -> Union[dict, str]:
        if mode == ResultMode.dict:
            return self.__videoComponent
        elif mode == ResultMode.json:
            return json.dumps(self.__videoComponent, indent=4)

    def __getVideoComponent(self, mode: str) -> None:
        videoComponent = {}

        try:
            self.__videoComponent
        except:
            self.__videoComponent = {}
            pass

        #Putting this first to avoid the publish data switch in the other modes
        if mode in ['getNextInfo', None]:
            try:
                responseSource = self.nextResponseSource
            except:
                responseSource = None

            videorenderer: list = getValue(responseSource, ["playerOverlays", "playerOverlayRenderer", "endScreen", "watchNextEndScreenRenderer", "results"])
            videos = []
            for video in videorenderer:
                try:
                    video = video["endScreenVideoRenderer"]
                    j = {
                        "isPlaylist" : False,
                        "id": getValue(video, ["videoId"]),
                        "thumbnails": getValue(video, ["thumbnail", "thumbnails"]),
                        "title": getValue(video, ["title", "simpleText"]),
                        "channel": {
                            "name": getValue(video, ["shortBylineText", "runs", 0, "text"]),
                            "id": getValue(video, ["shortBylineText", "runs", 0, "navigationEndpoint", "browseEndpoint", "browseId"]),
                            "link": getValue(video, ["shortBylineText", "runs", 0, "navigationEndpoint", "browseEndpoint", "canonicalBaseUrl"]),
                        },
                        "duration": getValue(video, ["lengthText", "simpleText"]),
                        "accessibility": {
                            "title": getValue(video, ["title", "accessibility", "accessibilityData", "label"]),
                            "duration": getValue(video, ["lengthText", "accessibility", "accessibilityData", "label"]),
                        },
                        "link": "https://www.youtube.com" + getValue(video, ["navigationEndpoint", "commandMetadata", "webCommandMetadata", "url"]),
                        "isPlayable": getValue(video, ["isPlayable"]),
                        "videoCount": 1,
                    }
                    videos.append(j)
                    continue
                except:
                    pass

                try:
                    video = video["endScreenPlaylistRenderer"]
                    j = {
                        "isPlaylist" : True,
                        "id": getValue(video, ["playlistId"]),
                        "thumbnails": getValue(video, ["thumbnail", "thumbnails"]),
                        "title": getValue(video, ["title", "simpleText"]),
                        "channel": {
                            "name": getValue(video, ["shortBylineText", "runs", 0, "text"]),
                            "id": getValue(video, ["shortBylineText", "runs", 0, "navigationEndpoint", "browseEndpoint", "browseId"]),
                            "link": getValue(video, ["shortBylineText", "runs", 0, "navigationEndpoint", "browseEndpoint", "canonicalBaseUrl"]),
                        },
                        "duration": getValue(video, ["lengthText", "simpleText"]),
                        "accessibility": {
                            "title": getValue(video, ["title", "accessibility", "accessibilityData", "label"]),
                            "duration": getValue(video, ["lengthText", "accessibility", "accessibilityData", "label"]),
                        },
                        "link": "https://www.youtube.com" + getValue(video, ["navigationEndpoint", "commandMetadata", "webCommandMetadata", "url"]),
                        "isPlayable": getValue(video, ["isPlayable"]),
                        "videoCount": getValue(video, ["videoCount"]),
                    }
                    videos.append(j)
                    continue
                except:
                    pass
            
            component = {
                'recommendations': videos,
                'autoGeneratedCategory': getValue(responseSource, ['contents', 'twoColumnWatchNextResults', 'results', 'results', 'contents', 1, 'videoSecondaryInfoRenderer', 'metadataRowContainer', 'metadataRowContainerRenderer', 'rows', 0, 'richMetadataRowRenderer', 'contents', 0, 'richMetadataRenderer', 'title', 'simpleText']),
            }
            videoComponent.update(component)

            self.__videoComponent.update(videoComponent)

            #Return here to avoid the publish data switch in the other modes
            return
        if mode in ['getInfo', None]:
            try:
                responseSource = self.responseSource
            except:
                responseSource = None
            if self.enableHTML:
                responseSource = self.HTMLresponseSource
            component = {
                'id': getValue(responseSource, ['videoDetails', 'videoId']),
                'title': getValue(responseSource, ['videoDetails', 'title']),
                'duration': {
                    'secondsText': getValue(responseSource, ['videoDetails', 'lengthSeconds']),
                },
                'viewCount': {
                    'text': getValue(responseSource, ['videoDetails', 'viewCount'])
                },
                'thumbnails': getValue(responseSource, ['videoDetails', 'thumbnail', 'thumbnails']),
                'description': getValue(responseSource, ['videoDetails', 'shortDescription']),
                'channel': {
                    'name': getValue(responseSource, ['videoDetails', 'author']),
                    'id': getValue(responseSource, ['videoDetails', 'channelId']),
                },
                'allowRatings': getValue(responseSource, ['videoDetails', 'allowRatings']),
                'averageRating': getValue(responseSource, ['videoDetails', 'averageRating']),
                'keywords': getValue(responseSource, ['videoDetails', 'keywords']),
                'isLiveContent': getValue(responseSource, ['videoDetails', 'isLiveContent']),
                'publishDate': getValue(responseSource, ['microformat', 'playerMicroformatRenderer', 'publishDate']),
                'uploadDate': getValue(responseSource, ['microformat', 'playerMicroformatRenderer', 'uploadDate']),
                'isFamilySafe': getValue(responseSource, ['microformat', 'playerMicroformatRenderer', 'isFamilySafe']),
                'category': getValue(responseSource, ['microformat', 'playerMicroformatRenderer', 'category']),
                'hashtags': re.findall('#\w+', getValue(responseSource, ['videoDetails', 'shortDescription'])),
            }
            component['isLiveNow'] = component['isLiveContent'] and component['duration']['secondsText'] == "0"
            component['link'] = 'https://www.youtube.com/watch?v=' + component['id']
            component['channel']['link'] = 'https://www.youtube.com/channel/' + component['channel']['id']
            videoComponent.update(component)
        if mode in ['getFormats', None]:
            videoComponent.update(
                {
                    "streamingData": getValue(self.responseSource, ["streamingData"])
                }
            )
        if self.enableHTML:
            videoComponent["publishDate"] = getValue(self.HTMLresponseSource, ['microformat', 'playerMicroformatRenderer', 'publishDate'])
            videoComponent["uploadDate"] = getValue(self.HTMLresponseSource, ['microformat', 'playerMicroformatRenderer', 'uploadDate'])
        self.__videoComponent.update(videoComponent)
