from flask import Flask, render_template, request, redirect, flash, jsonify

app = Flask(__name__)
cwd = app.root_path

if app.config["ENV"] == "production":
    app.config.from_object("config.ProductionConfig")
else:
    app.config.from_object("config.DevelopmentConfig")

print(f'\n**ENV is set to: {app.config["ENV"]}**\n')

app.config['SESSION_TYPE'] = 'filesystem'
