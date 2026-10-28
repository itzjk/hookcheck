Output docs/demo.gif

Require hookcheck
Require ffmpeg
Require ffprobe

Set Shell "bash"
Set Width 1200
Set Height 720
Set FontSize 20
Set Padding 24
Set Theme "Dracula"
Set TypingSpeed 25ms
Set Framerate 15

Env HOOKCHECK_PROVIDER "none"
Env PS1 "$ "

Hide
Type "unset PROMPT_COMMAND; PS1='$ '; clear"
Enter
Sleep 500ms
Show

Type "hookcheck examples/delayed-action.mp4"
Enter
Wait+Line /^\$$/
Sleep 7s

Ctrl+L
Type "hookcheck examples/action-first.mp4"
Enter
Wait+Line /^\$$/
Sleep 6s
