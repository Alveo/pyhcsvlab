import unittest
import pyalveo
import os
import sqlite3
import shutil

class ClientTest(unittest.TestCase):


    def test_create_client(self):
        """ Test that the clients can be created with or without alveo.config file
        and correct database is created """

        # Test with wrong api key
        with self.assertRaises(pyalveo.APIError) as cm:
                client = pyalveo.Client(api_key="wrongapikey123")

        self.assertEqual(
            "HTTP 401\nUnauthorized\nClient could not be created. Check your api key",
            str(cm.exception)
        )

        alveo_config_path = os.path.expanduser('~/alveo.config')
        cache_db_path = 'tmp'

        # Test when alveo.config is present
        if os.path.exists(alveo_config_path):
            client = pyalveo.Client()
            self.assertEqual(type(client), pyalveo.Client)

        else:
            # Teset when alveo.config is absent
            with self.assertRaises(IOError) as cm:
                client = pyalveo.Client()

            self.assertEqual(
                "Could not find file ~/alveo.config. Please download your configuration file from http://pyalveo.org.au/ OR try to create a client by specifying your api key",
                str(cm.exception)
            )

        # Test with correct api key
        client = pyalveo.Client()
        self.assertEqual(type(client), pyalveo.Client)



    def test_client_cache(self):
        """Test that we can create a client with a cache enabled and that it caches things"""

        cache_dir = "tmp"

        client = pyalveo.Client(use_cache=True, cache_dir=cache_dir)

        item_url = client.api_url + "catalog/cooee/1-190"
        item_meta = ""


        self.addCleanup(shutil.rmtree, cache_dir, True)

        self.assertEqual(type(client.cache), pyalveo.Cache)

        item = client.get_item(item_url)

        self.assertEqual(type(item), pyalveo.Item)

        # look in the cache for this item metadata

        self.assertTrue(client.cache.has_item(item_url))

        meta = client.cache.get_item(item_url)

        # check a few things about the metadata json
        self.assertIn("@context", meta.decode('utf-8'))
        self.assertIn(item_url, meta.decode('utf-8'))


        # get a document
        doc = item.get_document(0)
        self.assertEqual(type(doc), pyalveo.Document)

        doc_content = doc.get_content()
        self.assertEqual(doc_content[:20].decode(), "\r\n\r\n\r\nSydney, New So")

        # there should be a cached file somewhere under cache_dir
        ldir = os.listdir(os.path.join(cache_dir, "files"))
        self.assertEqual(1, len(ldir))
        # the content of the file should be the same as our doc_content
        with open(os.path.join(cache_dir, "files", ldir[0]), 'rb') as h:
            self.assertEqual(h.read(), doc_content)

        # now trigger a cache hit
        doc_content_cache = doc.get_content()
        self.assertEqual(doc_content, doc_content_cache)



    def test_client_no_cache(self):
        """Test that we can create and use a client without a cache enabled"""


        client = pyalveo.Client(use_cache=False)

        item_url = client.api_url + "catalog/cooee/1-190"
        item_meta = ""

        item = client.get_item(item_url)

        self.assertEqual(type(item), pyalveo.Item)

        # get a document
        doc = item.get_document(0)
        self.assertEqual(type(doc), pyalveo.Document)

        doc_content = doc.get_content()
        self.assertEqual(doc_content[:20].decode(), "\r\n\r\n\r\nSydney, New So")



    def test_identical_clients(self):
        """ Test that multiple clients can be created with default configuration or specific configuration
        and check if they are identical or not """

        first_client = pyalveo.Client(use_cache=False)
        second_client = pyalveo.Client(use_cache=False)

        self.assertTrue(first_client.__eq__(second_client))
        self.assertTrue(second_client.__eq__(first_client))


        first_client = pyalveo.Client(cache="cache.db", use_cache=True, update_cache=True)
        second_client = pyalveo.Client(cache="cache.db", use_cache=True, update_cache=True)

        # Two clients created with same api key and same arguments must be same
        self.assertTrue(first_client.__eq__(second_client))
        self.assertTrue(second_client.__eq__(first_client))

        # Two clients with same api key but diffent database configuration must be different
        third_client = pyalveo.Client(cache="cache.db", use_cache=False, update_cache=False)
        self.assertTrue(first_client.__ne__(third_client))
        self.assertTrue(second_client.__ne__(third_client))

        # Client without any arguments should be equal to client with all the default arguments
        first_client = pyalveo.Client()
        second_client = first_client = pyalveo.Client(cache="cache.db", use_cache=True, update_cache=True)
        self.assertTrue(first_client.__eq__(second_client))


    def test_item_download(self):
        """Test access to individual items"""
        client = pyalveo.Client(use_cache=False)
        item_url = client.api_url + 'catalog/ace/A01a'
        item  = client.get_item(item_url)

        self.assertEqual(item_url, item.url())

        meta = item.metadata()

        self.assertEqual(meta['alveo:primary_text_url'], client.api_url + u'catalog/ace/A01a/primary_text.json')


    def test_item_lists(self):
        """ Test that the item list can be created, item can be added to the item list,
        item list can be renamed and deleted """

        client = pyalveo.Client(use_cache=False)
        base_url = client.api_url
        item_list_name = 'pyalveo_test_item_list'

        # check for an existing list and remove it if needed
        try:
            my_list = client.get_item_list_by_name(item_list_name)
            client.delete_item_list(my_list)
        except:
            pass

        new_item_url_1 = [base_url + 'catalog/ace/A01a']
        self.assertEqual(client.add_to_item_list_by_name(new_item_url_1, item_list_name), '1 items added to new item list ' + item_list_name)

        my_list = client.get_item_list_by_name(item_list_name)
        self.assertEqual(my_list.name(), item_list_name)


        new_item_url_2 = [base_url + 'catalog/ace/A01b']
        self.assertEqual(client.add_to_item_list(new_item_url_2, my_list.url()), '1 items added to existing item list ' + my_list.name())


        my_list = my_list.refresh()
        item = client.get_item(new_item_url_2[0])
        self.assertTrue(item in my_list)

        # Test Rename List
        client.rename_item_list(my_list, 'brand new list')
        my_list = my_list.refresh()
        self.assertEqual(my_list.name(), 'brand new list')

        # Deleting an Item List
        self.assertEqual(client.delete_item_list(my_list), True)

        # deleting an Item List that isn't there raises an exception
        self.assertRaises(pyalveo.APIError, client.delete_item_list, my_list)

    def test_get_annotations(self):

        client = pyalveo.Client(use_cache=False)
        item_with = client.get_item(client.api_url + "catalog/monash/MEBH2FB_Sanitised")
        item_without = client.get_item(client.api_url + "catalog/avozes/f6ArtharThan")

        # get annotations for this item of type 'speaker'
        anns = item_with.get_annotations(type=u'http://ns.ausnc.org.au/schemas/annotation/ice/speaker')
        self.assertListEqual(sorted(anns.keys()), [u'@context', u'alveo:annotations', u'commonProperties'])

        ann = anns['alveo:annotations'][0]
        self.assertEqual(sorted(ann.keys()), [u'@id', u'@type',  u'end',  u'start', u'type'])

        # this one has no annotations
        anns = item_without.get_annotations(type=u'http://ns.ausnc.org.au/schemas/annotation/ice/speaker')
        self.assertEqual(anns, None)

    def test_sparql_query(self):
        """Can we run a simple SPARQL query"""

        client = pyalveo.Client()

        query = """select * where { ?a ?b ?c } LIMIT 10"""

        result = client.sparql_query('mitcheldelbridge', query)

        self.assertIn('results', result)
        self.assertIn('bindings', result['results'])
        self.assertEqual(len(result['results']['bindings']), 10)


if __name__ == "__main__" :
    unittest.main(verbosity=5)
