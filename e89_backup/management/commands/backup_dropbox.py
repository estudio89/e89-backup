from django.core.management.base import BaseCommand, CommandError
from django.db.models import get_model
from django.conf import settings
from django.utils import timezone
import e89_tools.tools

import os
import dropbox
import zipfile
import datetime as dt


class Command(BaseCommand):
	args = ''
	help = 'Envia o arquivo de backup do banco de dados, assim como os arquivos da pasta media para o dropbox.'

	def handle(self, *args, **options):

		KeyValueStore = get_model('e89_tools', 'KeyValueStore')
		contador = KeyValueStore.get_int('backup.contador',1)
		frequencia = settings.DB_BACKUP_FREQUENCY

		if contador < frequencia:
			KeyValueStore.set_value('backup.contador',contador+1)
			self.stdout.write('Backup sera realizado daqui a %d dias...' % (frequencia-contador))
			return
		else:
			KeyValueStore.set_value('backup.contador',1)

		client = dropbox.client.DropboxClient(settings.DB_BACKUP_DROPBOX_AUTHORIZATION_CODE)


		self.stdout.write('[' + self.get_now() + '] Enviando backup sql...')
		try:
			tempfile_path = os.path.abspath(os.path.join(settings.DB_BACKUP_FILE_PATH,'..','temp.sql.zip'))
			zf=zipfile.ZipFile(tempfile_path,mode='w',compression=zipfile.ZIP_DEFLATED)
			zf.write(settings.DB_BACKUP_FILE_PATH)
			zf.close()
			fobj = open(tempfile_path,'r')
		except IOError:
			raise CommandError('Arquivo de backup do banco nao encontrado no caminho %s. Verifique opcao DB_BACKUP_FILE_PATH no arquivo settings.py')

		url = '/backups/%s_backup.sql.zip'%(timezone.localtime( timezone.now() ).strftime('%Y_%m_%d'))
		client.put_file(url,fobj)
		fobj.close()
		os.remove(tempfile_path)
		self.stdout.write('[' + self.get_now() + '] Backup sql enviado.')




		self.stdout.write('[' + self.get_now() + '] Comprimindo arquivos...')
		tempfile_path = os.path.abspath(os.path.join(settings.DB_BACKUP_FILE_PATH,'..','temp.zip'))
		zobj = zipfile.ZipFile(tempfile_path,mode='w',compression=zipfile.ZIP_DEFLATED)
		e89_tools.tools.zip_directory(zobj, settings.DB_BACKUP_DIRECTORY)
		zobj.close()
		self.stdout.write('[' + self.get_now() + '] Compressao finalizada.')




		self.stdout.write('[' + self.get_now() + '] Enviando arquivos...')
		fobj = open(tempfile_path,'r')
		url = '/backups/%s_files.zip'%( timezone.localtime( timezone.now() ).strftime('%Y_%m_%d') )
		client.put_file(url,fobj)
		fobj.close()
		os.remove(tempfile_path)
		self.stdout.write('[' + self.get_now() + '] Arquivos enviados.')



		self.stdout.write('[' + self.get_now() + '] Excluindo backups SQL antigos...')
		url = '/backups/%s_backup.sql.zip'%( timezone.localtime( timezone.now() -  dt.timedelta(days=frequencia*settings.DB_BACKUP_MAX_KEEP)).strftime('%Y_%m_%d') )
		try:
			client.file_delete(url)
		except dropbox.rest.ErrorResponse:
			pass

		self.stdout.write('[' + self.get_now() + '] Excluindo backups de arquivos antigos...')
		url = '/backups/%s_files.zip'%( timezone.localtime( timezone.now() -  dt.timedelta(days=frequencia*settings.DB_BACKUP_MAX_KEEP)).strftime('%Y_%m_%d') )
		try:
			client.file_delete(url)
		except dropbox.rest.ErrorResponse:
			pass

		self.stdout.write('[' + self.get_now() + '] Backup finalizado com sucesso!')


	def get_now(self):
		return timezone.localtime( timezone.now() ).strftime('%Y-%m-%d %H:%M')