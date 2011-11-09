from chained import Chain
from chained.tests.server.models import Author, Book, Chapter

class LibraryChain(Chain):
	class Meta:
		models = [Author, Book, Chapter]