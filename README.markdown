Chained
=======

A cascading selection app for Django. Also, the exact opposite of the upcoming Tarantino film.

Chain
-----
A class that links models together.

It's defined like this:

_library.chains_

```python
from chained import Chain
from library.models import Author, Book, Chapter

class LibraryChain(Chain):
	class Meta:
		models = [Author, Book, Chapter]
```

This creates a Chain that exposes 'author', 'book', and 'chapter' members.

Each of these ChainLinks exposes the members of the related model, along with selection methods. When a selection method is used at a particular level of the Chain, the other levels cascade alongside.

For example, the above class would be used like this:

_library.views_

```python
from library.chains import LibraryChain

def get_dinosaur_book(request):
	...
	library_chain = LibraryChain()

	library_chain.book.select(Book.objects.get(name="Jurassic Park"))
	
	# library_chain.author is now Michael Crichton, and 
	# library_chain.chapter is now the first chapter of Jurassic Park

	return render_to_response("library/book_info.html")
```

_library/book_info.html_

```html
<html>
	<head>
		<title>{{ library_chain.book.title }}</title>
	</head>
	<body>
		<dl>
			<dt>Title</dt>
			<dd>{{ library_chain.book.title }}</dd>
			<dt>Author</dt>
			<dd>{{ library_chain.author.full_name }}</dd>
		</dl>
	</body>
</html>
```

FormChain
---------
Links ModelForms together, but it exposes a property called 'form'. It is defined like so:

_library.chains_

```python
from chained import FormChain
from library.models import Author, Book, Chapter
from library.forms import AuthorForm, BookForm, ChapterForm

class LibraryFormChain(FormChain):
	class Meta:
		models = [Author, Book, Chapter]
		forms = [AuthorForm, BookForm, ChapterForm]
```

When an item is selected on this Chain, this 'form' property will be set to the associated ModelForm with the instance property set to the newly selected item. 

This form can now be rendered in templates.