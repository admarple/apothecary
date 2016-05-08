from flask import Flask, render_template

app = Flask(__name__)
app.config.from_object('websiteconfig')

nav_bar = [{"href": '/', "id": 'index', "caption": 'a M t'},
           {"href": '/story/', "id": 'story', "caption": 'Our Story'}]
toes = [{"href": 'https://github.com/admarple/apothecary', "id": 'github', "caption": 'Source on GitHub'}]
him = 'Alex Marple'
her = 'Tatiana McLauchlan'
title = her.split(' ')[0] + ' & ' + him.split(' ')[0]


@app.route('/')
def index():
    return render_template('index.html',
                           her=her,
                           him=him,
                           title=title,
                           nav_bar=nav_bar,
                           toes=toes)


@app.route('/story/')
def story():
    section_type = 'story'
    sections = [{"title": 'Tatiana', "text": 'Tatiana is the best :D'},
                {"title": 'Alex', "text": 'Alex is a shit ball :P'},
                {'title': 'Our Story', "text": 'Tat and Alex met in 2010 in Philadelphia. Their relationship' +
                                               ' has taken them (by different paths) to New York.'}]
    return render_template('sections.html',
                           sections=sections,
                           section_type=section_type,
                           title=title,
                           nav_bar=nav_bar,
                           toes=toes)
