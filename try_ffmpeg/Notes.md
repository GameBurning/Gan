##Try HTML5 HLS stream(m3u8 listed .ts videos via http)

```
ffmpeg -i http://pl-hls3.live.panda.tv/live_panda/69b7dec04c5547c232707127a401cee5.m3u8 -c copy -bsf:a aac_adtstoasc output.mp4
```
```
ffmpeg -i http://pl-hls3.live.panda.tv/live_panda/69b7dec04c5547c232707127a401cee5.m3u8 -f segment -segment_list out.list -segment_time 60 -segment_wrap 24 out%03d.mp4
```
```
ffmpeg -i http://pl-hls3.live.panda.tv/live_panda/35e509f3619387054a690efe4369bbb3.m3u8 -c copy -flags +global_header -f segment -bsf:a aac_adtstoasc -segment_time 60 -segment_format_options movflags=+faststart -reset_timestamps 1 test_hls_%d.mp4
```
```
ffmpeg -f concat -i inputs.txt -vcodec copy -acodec copy Total.mp4
```

##Try flv via http long connection
```
ffmpeg -i http://220.243.194.31/pl3.live.panda.tv/live_panda/35e509f3619387054a690efe4369bbb3.flv -c copy output.flv
```
```
ffmpeg -i http://220.243.194.31/pl3.live.panda.tv/live_panda/35e509f3619387054a690efe4369bbb3.flv -c copy -f segment -segment_time 20 -reset_timestamps 1 test_flv_%d.flv
```

##拼接视频
```
ffmpeg -f concat -i inputs.txt -vcodec copy -acodec copy Total.flv
```