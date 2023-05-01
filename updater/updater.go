package main

import (
	"context"
	"crypto/sha256"
	"crypto/tls"
	"encoding/hex"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/jdferrell3/peinfo-go/peinfo"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/schollz/progressbar/v3"
)

// module main
func CheckUpdates() {
	endpoint := "data.corems-dev.emsl.pnl.gov"
// 	accessKeyID := 
// 	secretAccessKey :=
	useSSL := true
	// skipCert := true

	bucket := "uploader-dl"
	// zipname := "watchdog_daemon.zip"
	exename := "local_api.exe"
	cfgname := "config.toml.example"
	updname := "update_uploader.bat"
	verfile := "uploader_version.txt"

	fileList := make([]string, 3)
	fileList[0] = exename
	fileList[1] = updname
	fileList[2] = verfile
	// enableVT100Mode(os.Stdout.Fd())
	// enableVT100Mode(os.Stderr.Fd())
	// Initialize minio client object.

	// // Keep TLS config.
	// tlsConfig := &tls.Config{}
	// if useSSL && skipCert {
	// 	tlsConfig.InsecureSkipVerify = true
	// }

	// var transport http.RoundTripper = &http.Transport{
	// 	Proxy: http.ProxyFromEnvironment,
	// 	DialContext: (&net.Dialer{
	// 		Timeout:   30 * time.Second,
	// 		KeepAlive: 30 * time.Second,
	// 	}).DialContext,
	// 	MaxIdleConns:          100,
	// 	IdleConnTimeout:       90 * time.Second,
	// 	TLSHandshakeTimeout:   10 * time.Second,
	// 	ExpectContinueTimeout: 1 * time.Second,
	// 	TLSClientConfig:       tlsConfig,
	// 	// Set this value so that the underlying transport round-tripper
	// 	// doesn't try to auto decode the body of objects with
	// 	// content-encoding set to `gzip`.
	// 	//
	// 	// Refer:
	// 	//    https://golang.org/src/net/http/transport.go?h=roundTrip#L1843
	// 	DisableCompression: true,
	// }

	// Set custom transport.
	// api.SetCustomTransport(transport)
	// api.SetCustomTransport(&http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}})
	minioClient, err := minio.New(endpoint, &minio.Options{
		Creds:     credentials.NewStaticV4(accessKeyID, secretAccessKey, ""),
		Secure:    useSSL,
		Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}},
	})
	if err != nil {
		log.Fatalln(err)
	}

	// log.Printf("%#v\n", minioClient) // minioClient is now setup
	getMinioObj := func(objName string) (*minio.Object, minio.ObjectInfo, error) {
		objStat, _ := minioClient.StatObject(context.Background(), bucket, objName, minio.GetObjectOptions{})
		object, err := minioClient.GetObject(context.Background(), bucket, objName, minio.GetObjectOptions{})
		if err != nil {
			return object, objStat, err
		}
		return object, objStat, err
	}

	object, _, _ := getMinioObj(verfile)
	{
	}
	remote_ver, err := io.ReadAll(object)
	if err != nil {
		log.Println(err)
		return
	}
	defer object.Close()
	// fmt.Println(string(remote_ver))
	remote_str := string(remote_ver)
	remote_str = strings.TrimSuffix(remote_str, "\r\n")
	remote_str_cmp := VersionOrdinal(remote_str)
	fmt.Printf("Remote version is: %s\n", remote_str)
	// local_ver, err := os.ReadFile("./uploader_version.txt")
	// local_ver, err := exec.Command("wine", "./local_api.exe", "--version").CombinedOutput()
	// command := fmt.Sprintf("(Get-Command %v).FileVersionInfo.FileVersion", "./local_api.exe")
	// local_ver, _ := exec.Command("powershell.exe", "-c", command).CombinedOutput()
	file, err := peinfo.Initialize("./local_api.exe", false, ".", false)
	if err != nil {
		fmt.Println(err)
		return
	}
	var local_ver string
	vi, keys, err := file.GetVersionInfo()
	if nil == err && len(keys) > 0 {
		local_ver = fmt.Sprint(vi["FileVersion"])
	} else {
		local_ver = fmt.Sprintf("Error getting version info: %s\n", err)
	}
	file.OSFile.Close()
	// fmt.Println(local_ver)
	// local_str := string(local_ver[:])
	local_str := strings.TrimSuffix(local_ver, "\r\n")
	local_str_cmp := VersionOrdinal(local_str)
	fmt.Printf("Local version is : %s\n", local_str)
	// defer local_ver.Close()
	if local_str_cmp < remote_str_cmp {
		var s string
		fmt.Printf(`New version of uploader available (%s, current %s), download and update? (Y/N)`, remote_str, local_str)
		fmt.Scanln(&s)
		if strings.ToLower(s) == "y" {
			// fmt.Println("Key was yes!")
			exeobj, exestat, _ := getMinioObj(exename)
			{
			}
			exehashfile, _, _ := getMinioObj(exename + ".sha256")
			{
			}
			exehashdata, _ := io.ReadAll(exehashfile)
			cfghashfile, _, _ := getMinioObj(cfgname + ".sha256")
			{
			}
			cfghashdata, _ := io.ReadAll(cfghashfile)
			exebar := progressbar.NewOptions64(exestat.Size,
				progressbar.OptionSetDescription("downloading"),
				progressbar.OptionUseANSICodes(true),
				progressbar.OptionEnableColorCodes(true),
				progressbar.OptionShowBytes(true),
				progressbar.OptionSetWriter(os.Stderr),
				progressbar.OptionSetWidth(10),
				progressbar.OptionThrottle(65*time.Millisecond),
				progressbar.OptionShowCount(),
				progressbar.OptionOnCompletion(func() {
					fmt.Fprint(os.Stderr, "\n")
				}),
				progressbar.OptionSpinnerType(14),
				progressbar.OptionFullWidth(),
				progressbar.OptionSetRenderBlankState(true),
			)

			targetDir := "./"
			// extractFilePath := filepath.Join(targetDir, f.Name)
			exeOutputFile, err := os.OpenFile(filepath.Join(targetDir, exename+"-tmp"), os.O_WRONLY|os.O_CREATE|os.O_TRUNC, os.FileMode(int(0755)))
			if err != nil {
				log.Fatal(err)
			}
			// defer exeOutputFile.Close()
			exehash := sha256.New()
			cfghash := sha256.New()
			_, err = io.Copy(io.MultiWriter(exeOutputFile, exebar, exehash), exeobj)
			if err != nil {
				log.Fatal(err)
			}
			exeOutputFile.Close()
			cfgobj, _, _ := getMinioObj(cfgname)
			{
			}
			cfgOutputFile, err := os.OpenFile(filepath.Join(targetDir, cfgname+"-tmp"), os.O_WRONLY|os.O_CREATE|os.O_TRUNC, os.FileMode(int(0755)))
			if err != nil {
				log.Fatal(err)
			}
			_, err = io.Copy(io.MultiWriter(cfgOutputFile, cfghash), cfgobj)
			if err != nil {
				log.Fatal(err)
			}
			cfgOutputFile.Close()
			// fmt.Printf("%x\n%s\n", hash.Sum(nil), exehash)
			if hex.EncodeToString(exehash.Sum(nil)) == string(exehashdata[:]) {
				// fmt.Println("exe hashes match!")
				os.Rename(exename+"-tmp", exename)
				// print(exename + "-tmp")
				time.Sleep(250 * time.Millisecond)
			} else {
				fmt.Println("New local_api.exe failed hash check, local copy not updated!")
			}
			if hex.EncodeToString(cfghash.Sum(nil)) == string(cfghashdata[:]) {
				// fmt.Println("cfg hashes match!")
				os.Rename(cfgname+"-tmp", cfgname)
				// print(cfgname + "-tmp")
				time.Sleep(250 * time.Millisecond)
			} else {
				fmt.Println("New config.toml.example failed hash check, local copy not updated!")
			}

			os.Remove(exename + "-tmp")
			os.Remove(cfgname + "-tmp")
		} else {
			fmt.Println("key entered was", s, "exiting!")
		}
	} else {
		fmt.Println("Nothing to do!")
	}
}
func VersionOrdinal(version string) string {
	// ISO/IEC 14651:2011
	const maxByte = 1<<8 - 1
	vo := make([]byte, 0, len(version)+8)
	j := -1
	for i := 0; i < len(version); i++ {
		b := version[i]
		if '0' > b || b > '9' {
			vo = append(vo, b)
			j = -1
			continue
		}
		if j == -1 {
			vo = append(vo, 0x00)
			j = len(vo) - 1
		}
		if vo[j] == 1 && vo[j+1] == '0' {
			vo[j+1] = b
			continue
		}
		if vo[j]+1 > maxByte {
			panic("VersionOrdinal: invalid version")
		}
		vo = append(vo, b)
		vo[j]++
	}
	return string(vo)
}

// MakeZip := func(w) {
// 	zipWriter := zip.NewWriter(w)

// 	for _, entry := range fileList {
// 		header := &zip.FileHeader{
// 			Name:     entry,
// 			Method:   zip.Store, // deflate also works, but at a cost
// 			Modified: time.Now(),
// 		}
// 		entryWriter, err := zipWriter.CreateHeader(header)
// 		if err != nil {
// 			fmt.Println(err)
// 		}

// 		fileReader := bufio.NewReader(entry)

// 		_, err = io.Copy(entryWriter, fileReader)
// 		if err != nil {
// 			fmt.Println(err)
// 		}

// 		zipWriter.Flush()
// 		flushingWriter, ok := z.destination.(http.Flusher)
// 		if ok {
// 			flushingWriter.Flush()
// 		}
// 	}

// 	return zipWriter.Close()

// }

// zipsize, err := minioClient.StatObject(context.Background(), bucket, zipname, minio.GetObjectOptions{})
// if err != nil {
// 	fmt.Println(err)
// 	return
// }
// zipobj, err := minioClient.GetObject(context.Background(), bucket, zipname, minio.GetObjectOptions{})
// if err != nil {
// 	fmt.Println(err)
// 	return
// }
// r, err := zip.NewReader(zipobj, zipsize.Size)
// if err != nil {
// 	fmt.Println(err)
// 	return
// }
// cfgname := "no_clobber"

// for _, f := range r.File {
// 	targetDir := "./"
// 	extractFilePath := filepath.Join(targetDir, f.Name)
// 	fmt.Println(f.Name)
// 	if f.Name == "config.toml" {
// 		if checkFileExists(extractFilePath) {
// 			fmt.Println("found config")
// 			continue
// 		}
// 	}
// 	content, err := f.Open()
// 	if err != nil {
// 		log.Fatal(err)
// 	}
// 	if f.Name == "config.toml" {
// 		if checkFileExists(extractFilePath) {
// 			fmt.Println("found config")
// 			continue
// 		}
// 	}
// 	outputFile, err := os.OpenFile(extractFilePath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
// 	if err != nil {
// 		log.Fatal(err)
// 	}
// 	defer outputFile.Close()
// 	_, err = io.Copy(io.MultiWriter(outputFile, bar), content)
// 	if err != nil {
// 		log.Fatal(err)
// 	}
// }

// if _, err = io.Copy(localFile, object); err != nil {
// 	fmt.Println(err)
// 	return
