package main

import (
	"os"

	"golang.org/x/sys/windows"
)

func main() {

	enableVT100Mode(os.Stderr.Fd())

	CheckUpdates()

}

func enableVT100Mode(termHandle uintptr) error {
	dwMode := uint32(0)
	if err := windows.GetConsoleMode(windows.Handle(termHandle), &dwMode); err != nil {
		return err
	}
	const VTMode = windows.ENABLE_VIRTUAL_TERMINAL_PROCESSING
	if (dwMode & (VTMode)) == 0 {
		dwMode |= VTMode
		return windows.SetConsoleMode(windows.Handle(termHandle), dwMode)
	}
	return nil
}
