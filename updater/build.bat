set GOOS=windows&& ^
go build -v -ldflags="-s -w" . &&^
set GOOS=linux&&^
go build -v -ldflags="-s -w" . && ^
upx --lzma --best update_uploader.exe update_uploader && ^
copy update_uploader.exe ..\dist&&^
copy update_uploader ..\dist&&^
set GOOS=