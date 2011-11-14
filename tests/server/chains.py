from chained import Chain, FormChain
from chained.tests.server.models import Author, Book, Chapter
from chained.tests.server.forms import AuthorForm, BookForm, ChapterForm

class LibraryChain(Chain):
	class Meta:
		models = [Author, Book, Chapter]

class LibraryFormChain(FormChain):
	class Meta:
		models = [Author, Book, Chapter]
		form_classes = [AuthorForm, BookForm, ChapterForm]