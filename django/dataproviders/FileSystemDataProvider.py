"""Get and Put files, images and datasets for the COMIC framework

 History 
 20/06/2012    -     Sjoerd    -    Created this file

"""
import os
import glob
import pdb

import comicmodels.models


class FileSystemDataProvider:
    """ Get and Put files, images and datasets from and to filesystem """
             
    def __init__(self,dataDir):            
        self.dataDir = dataDir   
            
    
    def getImages(self,Project=""):
        """ get all images related to project """
        #images = ["image1.jpg","image2.jpg","image3.jpg"]
        
        os.chdir(self.dataDir)
        images = glob.glob("*.png")
        
        return images
    
    def getAllFileNames(self):
        """ get all images related to project as file objects"""
        #images = ["image1.jpg","image2.jpg","image3.jpg"]
        
        os.chdir(self.dataDir)
        filenames = glob.glob("*.*")
        filenames.sort()        
        return filenames
    
    
        
    
    
 