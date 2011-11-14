from django.forms import ModelForm

from chained.tests.server.models import Author, Book, Chapter

class AuthorForm(ModelForm):
	class Meta:
		model = Author

class BookForm(ModelForm):
	class Meta:
		model = Book

class ChapterForm(ModelForm):
	class Meta:
		model = Chapter