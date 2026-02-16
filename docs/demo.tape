# Hawaii Disco Demo GIF
# Run: vhs docs/demo.tape

# Output settings
Output docs/demo.gif
Set Theme "Dracula"
Set FontSize 14
Set Width 1200
Set Height 700
Set Padding 20
Set TypingSpeed 80ms
Set Shell zsh

# Launch app (hide command typing)
Hide
Type "source .venv/bin/activate && hawaiidisco"
Enter
Sleep 6s
Show

# Show the timeline for a moment
Sleep 2s

# Navigate articles with j/k
Type "j"
Sleep 500ms
Type "j"
Sleep 500ms
Type "j"
Sleep 500ms
Type "j"
Sleep 500ms
Type "k"
Sleep 1s

# Open article with Enter
Enter
Sleep 2.5s

# Scroll down in article
Type "j"
Sleep 250ms
Type "j"
Sleep 250ms
Type "j"
Sleep 250ms
Type "j"
Sleep 250ms
Type "j"
Sleep 1s

# Close article
Escape
Sleep 1s

# Bookmark the article
Type "b"
Sleep 1.5s

# Add memo to bookmark
Type "m"
Sleep 1s
Type "Great article - follow up later"
Sleep 500ms
Ctrl+S
Sleep 1.5s

# Open bookmark list
Type "l"
Sleep 2.5s

# Close bookmark list
Escape
Sleep 1s

# Search for articles
Type "/"
Sleep 800ms
Type "AI"
Enter
Sleep 2s

# Clear search
Escape
Sleep 1s

# Quit
Hide
Type "q"
Sleep 1s
