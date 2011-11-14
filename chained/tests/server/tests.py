from django.test import TestCase

from chained.tests.server.models import Author, Book, Chapter
from chained.tests.server.chains import LibraryChain, LibraryFormChain

class ChainTests(TestCase):
	"""
	Tests the regular Chain class.
	"""

	fixtures = ['library.json',]

	def setUp(self):
		self.libraryChain = LibraryChain()
	
	def testSelect(self):
		# make sure selecting an object provides the right data
		self.libraryChain.author.get_select(last_name="Wallis")
		self.assertEquals(self.libraryChain.book.title,"Try Hard")

		self.libraryChain.author.get_select(last_name="Cross")
		self.assertEquals(self.libraryChain.book.title,"The Second to Last Samurai")
	
	def testCreateTopLevel(self):
		# make a new author
		self.libraryChain.author = Author(last_name="Kidman")
		self.libraryChain.author.save()

		# check that it was saved
		self.assertTrue(Author.objects.filter(last_name="Kidman").exists())

	def testCreateM2M(self):
		# make the new book
		self.libraryChain.author.get_select(last_name="Cross")
		self.libraryChain.book = Book(title="The Third to Last Samurai")
		self.libraryChain.book.save()

		# check that it was saved
		self.assertTrue(Book.objects.filter(title="The Third to Last Samurai").exists())

		# ensure that it has the correct author added
		book = Book.objects.get(title="The Third to Last Samurai")
		self.assertTrue(book.authors.filter(last_name="Cross").exists())
	
	def testConnectM2MParent(self):
		# connect a new author to a book
		self.libraryChain.author.get_select(last_name="Stabley")
		self.libraryChain.author.book_set.add(Book.objects.get(title="Ghast"))
		self.libraryChain.author.save()

		book = Book.objects.get(title="Ghast")
		self.assertTrue(book.authors.filter(last_name="Stabley").exists())
	
	def testSiblingAccess(self):
		self.libraryChain.book.get_select(title="Ghast")
		self.assertEquals(self.libraryChain.chapter.title, "A New Apartment")

		self.libraryChain.chapter.select_next_sibling()
		self.assertEquals(self.libraryChain.chapter.title, "Willy's Gun")

		self.libraryChain.chapter.select_last()
		self.assertEquals(self.libraryChain.chapter.title, "Way Too Much Pottery")

		self.libraryChain.chapter.select_previous_sibling()
		self.assertEquals(self.libraryChain.chapter.title, "The Psychic")

		self.libraryChain.chapter.select_first()
		self.assertEquals(self.libraryChain.chapter.title, "A New Apartment")

	def testDelete(self):
		self.libraryChain.author.get_select(last_name="Wallis")

		self.libraryChain.book.delete()
		self.assertFalse(self.libraryChain.book.selected())

		self.libraryChain.author.delete()
		self.assertEquals(self.libraryChain.author.instance, Author.objects.get(last_name="Cross"))

class FormChainTests(TestCase):
	"""
	Tests the FormChain class.
	"""

	fixtures = ['library.json',]

	def setUp(self):
		self.libraryFormChain = LibraryFormChain()
	
	def testFormAccess(self):
		self.libraryFormChain.author.get_select(last_name="Pie")
		self.assertNotEqual(self.libraryFormChain.author.form, None)

		expected_output = ('<tr><th><label for="id_first_name">First name'+
				':</label></th><td><input id="id_first_name" type="text" '+
				'name="first_name" value="Who" maxlength="35" /></td></tr'+
				'>\n<tr><th><label for="id_last_name">Last name:</label></t'+
				'h><td><input id="id_last_name" type="text" name="last_na'+
				'me" value="Pie" maxlength="35" /></td></tr>')
		self.assertEquals(str(self.libraryFormChain.author.form),
				expected_output)
		