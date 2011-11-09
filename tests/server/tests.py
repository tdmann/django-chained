from django.utils import unittest

from chained.tests.server.models import Author, Book, Chapter
from chained.tests.server.forms import AuthorForm, BookForm, ChapterForm
from chained.tests.server.chains import LibraryChain, LibraryFormChain

class ChainTests(unittest.TestCase):
	"""
	Tests the regular Chain class.
	"""

	def setUp(self):
		self.libraryChain = LibraryChain()
		pass
	
	def testSelect(self):
		self.libraryChain.author.select(last_name="Willis")
		self.assertEquals(self.libraryChain.book.title,"Try Hard")
	
	def testCreateTopLevel(self):
		# make a new author
		self.libraryChain.author = Author(last_name="Kidman")
		self.libraryChain.author.save()

		# check that it was saved
		self.assertTrue(Author.objects.filter(last_name="Kidman").exists())

	def testCreateM2M(self):
		# make the new book
		self.libraryChain.author.select(last_name="Cruise")
		self.libraryChain.book = Book(title="The Second to Last Samurai")
		self.libraryChain.book.save()

		# check that it was saved
		self.assertTrue(Book.objects.exists(title="The Second to Last Samurai"))

		# ensure that it has the correct author added
		book = Book.objects.get(title="The Second to Last Samurai")
		self.assertTrue(book.authors.exists(last_name="Cruise"))

class FormChainTests(unittest.TestCase):
	"""
	Tests the form chain class.
	"""

	def testSaveFormData(self):
		libraryFormChain = LibraryFormChain()