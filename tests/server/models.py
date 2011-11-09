from django.db import models

class Author(models.Model):
	first_name = models.CharField(max_length=35)
	last_name = models.CharField(max_length=35)

	def __unicode__(self):
		return "%s %s" % (self.first_name, self.last_name)

class Book(models.Model):
	title = models.CharField(max_length=100)
	authors = models.ManyToManyField(Author)

	def __unicode__(self):
		return "%s" % self.title

class Chapter(models.Model):
	book = models.ForeignKey(Book)
	number = models.IntegerField()
	title = models.CharField(max_length=100)

	def __unicode__(self):
		return "%d. %s" % (self.number, self.title)