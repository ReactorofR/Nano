from django.db import models
import os,math

class Tag(models.Model):
	tag = models.CharField(max_length=50,unique=True)
	def __str__(self):
		return str(self.tag)


class QtAnimeGirl(models.Model):
	id = models.AutoField(primary_key=True,unique=True)
	name = models.CharField(max_length=40, blank=True)
	elo = models.IntegerField(default = 1000)
	image = models.CharField(max_length=100, unique=True)
	tags = models.ManyToManyField(Tag)

	def __str__(self):
		if len(self.name)<1:
			return str(self.id)
		else:
			return self.name	

	def getAllGirls(self,path='/images/'):
		for path in os.listdir(path):
			a = QtAnimeGirl()
			a.image = path
			a.save()

	def getNewGirls(self,path='/images/'):
		new_girl_count = 0
		for image in os.listdir(path):
			try:
				a = QtAnimeGirl.objects.get(image=image)
			except QtAnimeGirl.DoesNotExist:
				print('Adding new girl with image {}'.format(image))
				a = QtAnimeGirl()
				a.image = image
				a.save()
				new_girl_count += 1

		return new_girl_count


	def updateELO(self,eloOpponent,score):
		expectedA = 1/(1+pow(10,((eloOpponent-self.elo)/400)))
		self.elo = round(self.elo + 32 * (score-expectedA))
		self.save()

	def addTag(self,tag):
		#check if tag exists
		try:
			self.tags.get(tag=tag)
		except Tag.DoesNotExist:
			try:
				new_tag = Tag.objects.get(tag=tag)
			except Tag.DoesNotExist:
				new_tag = Tag(tag=tag)
				new_tag.save()
			self.tags.add(new_tag)
			self.save()