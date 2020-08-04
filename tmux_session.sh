#!/bin/sh

# Set Session Name
WINDOW="gilson_app"
DIR_PATH="/Users/trinhsk/Documents/GitRepos/gilson_webapp/app"
WINDOWEXISTS=$(tmux list-windows | grep $WINDOW)

# Only create tmux window if it doesn't already exist
if [ "$WINDOWEXISTS" = "" ]
then
    # Start New Session with our name
    tmux new-window -d -n $WINDOW -c $DIR_PATH

    tmux rename-window -t 1 $WINDOW

    tmux select-window -t $WINDOW
    tmux selectp -t 0
    tmux send-keys -t $WINDOW "nvim" C-m
    tmux splitw -h -p 40
    tmux selectp -t 1
    # tmux send-keys -t $WINDOW 'echo "this is the flask environment"'
    tmux send-keys -t $WINDOW 'cd ' $DIR_PATH C-m 'conda activate rq-redis' C-m  C-m 'export FLASK_ENV=development' C-m 'python app.py' C-m

    # # # Create and setup pane for redis server
    tmux selectp -t 1
    tmux splitw -v -p 25
    tmux send-keys 'rediserv' C-m

    # # # Setup rq workers
    tmux selectp -t 1
    tmux splitw -h -p 50
    tmux send-keys 'cd ' $DIR_PATH C-m 'conda activate rq-redis' C-m 'python worker.py' C-m
fi
