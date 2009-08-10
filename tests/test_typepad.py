import httplib2
from httplib import HTTPException
import logging
import os
import unittest
from urllib import urlencode, unquote
from urlparse import urlsplit, urlunsplit, urlparse

import nose
from oauth import oauth

import typepad

from tests import utils
from tests import test_api


try:
    import json
except:
    import simplejson as json

from pprint import pprint


def load_test_data(filename=None):
    print("loading test data...")
    if filename is None:
        filename = os.path.join(os.path.dirname(__file__),
            "test_typepad.json")
    f = open(filename, "r")
    s = f.read()
    f.close()
    return json.loads(s)


def setUpModule():
    global testdata
    testdata = load_test_data()
    typepad.client.endpoint = testdata['configuration']['backend_url']
    if os.getenv('TP_MICROSCOPE'):
        typepad.client.cookies['tp_microscope'] = '1'
        typepad.client.cookies['pheno_stage'] = '1'


class TestTypePad(unittest.TestCase):

    def setUp(self):
        """ Configures the test class prior to each test method. """

        if not os.getenv('TEST_TYPEPAD'):
            raise nose.SkipTest('no TypePad tests without TEST_TYPEPAD=1')

        global testdata

        if 'application' not in testdata:
            raise nose.SkipTest('cannot run tests without application in test data')
        if 'configuration' not in testdata:
            raise nose.SkipTest('cannot run tests without configuration in test data')

        self.testdata = testdata
        self.configuration = self.testdata['configuration']

    def group_credentials(self):
        """ Establishes credentials as the group itself. """

        consumer = oauth.OAuthConsumer(
            self.configuration['oauth_consumer_key'],
            self.configuration['oauth_consumer_secret'],
        )
        token = oauth.OAuthToken(
            self.configuration['oauth_general_purpose_key'],
            self.configuration['oauth_general_purpose_secret'],
        )
        backend = urlparse(self.configuration['backend_url'])
        typepad.client.clear_credentials()
        typepad.client.add_credentials(consumer, token, domain=backend[1])
        return True

    def admin_credentials(self):
        """ Establishes credentials for a group administrator. """

        return False
        consumer = oauth.OAuthConsumer(
            self.configuration['oauth_consumer_key'],
            self.configuration['oauth_consumer_secret'],
        )
        token = self.testdata['admin']['oauth_token']
        backend = urlparse(self.configuration['backend_url'])
        typepad.client.clear_credentials()
        typepad.client.add_credentials(consumer, token, domain=backend[1])
        return True

    def member_credentials(self):
        """ Establishes credentials for a regular group member. """

        return False
        consumer = oauth.OAuthConsumer(
            self.configuration['oauth_consumer_key'],
            self.configuration['oauth_consumer_secret'],
        )
        token = self.testdata['member']['oauth_token']
        backend = urlparse(self.configuration['backend_url'])
        typepad.client.clear_credentials()
        typepad.client.add_credentials(consumer, token, domain=backend[1])
        return True

    def clear_credentials(self):
        typepad.client.clear_credentials()

    def select_group(self):
        return typepad.Group.get_by_url_id(
            self.testdata['application']['owner']['urlId'],
        )

    def admin_user(self):
        if 'admin' not in self.testdata: return None
        return typepad.User.from_dict(self.testdata['admin']['object'])

    def member_user(self):
        if 'member' not in self.testdata: return None
        return typepad.User.from_dict(self.testdata['member']['object'])

    def testApplication(self):
        """ Application.get_by_api_key -> /applications/apikey.json """

        self.group_credentials()

        # Collect Application request
        typepad.client.batch_request()
        app = typepad.Application.get_by_api_key(
            self.testdata['application']['apiKey'],
        )
        typepad.client.complete_batch()

        self.assertEquals(self.configuration['oauth_consumer_key'],
            self.testdata['application']['apiKey'],
            "OAuth consumer key and test application apiKey should match")

        test_app = typepad.Application.from_dict(
            self.testdata['application'],
        )

        # sigh, sort these consistently, since they aren't
        # reliably given by the API even though they are listed in
        # an array structure
        d1 = app.to_dict()
        d1['links'].sort()
        d2 = test_app.to_dict()
        d2['links'].sort()

        # Test the application was returned properly
        self.assertEquals(d1, d2,
            "test application should match application from api")

        # Also test that the owner was loaded through the application request
        # and it matches what we expect
        self.assertEquals(app.owner.to_dict(), test_app.owner.to_dict(),
            "test application group owner should match group from api")

    def testApplicationFailure(self):

        self.group_credentials()

        # TODO: we should test both an invalid request and a request
        # for a valid application that the group credentials has no
        # rights to access.

        typepad.client.batch_request()
        app = typepad.Application.get_by_api_key(
            self.testdata['application']['apiKey'] + "foobar"
        )
        self.assertRaises(HTTPException, typepad.client.complete_batch)


    def testGroup(self):
        """ Group.get_by_url_id -> /groups/xid.json """

        self.group_credentials()

        # Collect Group request
        typepad.client.batch_request()
        group = self.select_group()
        typepad.client.complete_batch()

        self.assert_(group._location, "Group location is not set")
        self.assertEquals(typepad.xid_from_atom_id(group.id),
            group.url_id,
            "Derived xid should match match url_id for group")

        test_group = typepad.Group.from_dict(
            self.testdata['application']['owner'],
        )
        self.assertEquals(group.to_dict(), test_group.to_dict())

        self.assert_(group.links['self'],
            "returned group should have a 'self' link relation")

    def testGroupFailure(self):

        self.group_credentials()

        # TODO: we should test both an invalid request and a request
        # for a valid group that the group credentials has no rights to
        # access.

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(
            self.testdata['application']['owner']['urlId'] + "foobar"
        )
        self.assertRaises(HTTPException, typepad.client.complete_batch)

    def testGroupEvents(self):
        """ Group.events -> /groups/xid/events.json

        This is similar to the Motion group events view. """

        if 'group_events' not in self.testdata:
            raise nose.SkipTest('cannot testGroupEvents without group_events in test data')

        self.group_credentials()

        loe = typepad.ListOf(typepad.Event)

        test_events = loe.from_dict(self.testdata['group_events'])
        num = len(test_events)

        self.assert_(num >= 1,
            "testdata group events should be non-empty")
        self.assert_(num <= 50,
            "testdata group events should not exceed 50")

        typepad.client.batch_request()
        group = self.select_group()
        events = group.events.filter(max_results=num, start_index=1)
        # lets also select the events in two portions to test the start-index
        # parameter for /groups/xid/events.json.
        events1 = group.events.filter(max_results=5, start_index=1)
        if num > 5:
            events2 = group.events.filter(max_results=num-5, start_index=6)
        typepad.client.complete_batch()

        self.assert_(group, "group request should succeed")
        self.assert_(group._location,
            "group should be returned with _location")

        self.assertEquals(len(events), num,
            "number of events retrieved should match requested size")
        if num > 5:
            self.assertEquals(len(events1) + len(events2), num,
                "number of events retrieved for set 1 and set 2 should equal %d" %
                num)

        self.assertEquals(events.total_results,
            test_events.total_results,
            "retrieved totalResults should match totalResults in test data")

        self.assertEquals(events1.total_results,
            test_events.total_results,
            "subset totalResults should match totalResults in test data")
        if num > 5:
            self.assertEquals(events2.total_results,
                test_events.total_results,
                "subset totalResults should match totalResults in test data")

        events_dict = events.to_dict()
        self.assertEquals(events_dict, test_events.to_dict())

    def testGroupMembers(self):
        """ Group.memberships -> /groups/xid/memberships.json """

        if 'group_members' not in self.testdata:
            raise nose.SkipTest('cannot testGroupUsers without group_members in test data')

        self.group_credentials()
        lor = typepad.ListOf(typepad.Relationship)

        test_members = lor.from_dict(self.testdata['group_members'])
        num = len(test_members)

        self.assert_(num >= 1,
            "test data group members should be non-empty")
        self.assert_(num <= 50,
            "test data group members should not exceed 50")

        typepad.client.batch_request()
        group = self.select_group()
        members = group.memberships.filter(max_results=num, start_index=1)
        members1 = group.memberships.filter(max_results=5, start_index=1)
        if num > 5:
            members2 = group.memberships.filter(max_results=num-5, start_index=6)
        typepad.client.complete_batch()

        self.assertEquals(len(members), num,
            "number of members retrieved should match requested size")
        if num > 5:
            self.assertEquals(len(members1) + len(members2), num,
                "number of members retrieved for set 1 and set 2 should equal %d" %
                num)

        self.assertEquals(members.total_results,
            test_members.total_results,
            "retrieved totalResults should match totalResults in test data")

        self.assertEquals(members1.total_results,
            test_members.total_results,
            "subset totalResults should match totalResults in test data")
        if num > 5:
            self.assertEquals(members2.total_results,
                test_members.total_results,
                "subset totalResults should match totalResults in test data")

        members_dict = members.to_dict()
        self.assertEquals(members_dict, test_members.to_dict())

    def testMember(self):
        """ User.get_by_url_id -> /users/xid.json """

        if 'member' not in self.testdata:
            raise nose.SkipTest('cannot testMember without member in test data')

        self.group_credentials()
        test_member = self.member_user()

        typepad.client.batch_request()
        member = typepad.User.get_by_url_id(test_member.url_id)
        typepad.client.complete_batch()

        self.assert_(member, "member request should succeed")
        self.assert_(member._location,
            "member should be returned with _location")

        self.assertEquals(member.to_dict(), test_member.to_dict())

    def testAdmin(self):
        """ User.get_by_url_id -> /users/xid.json """

        if 'admin' not in self.testdata:
            raise nose.SkipTest('cannot testAdmin without admin in test data')

        self.group_credentials()
        test_admin = self.admin_user()

        typepad.client.batch_request()
        admin = typepad.User.get_by_url_id(test_admin.url_id)
        group = self.select_group()
        admins = group.memberships.filter(admin=True)
        typepad.client.complete_batch()

        self.assert_(admin, "admin request should succeed")
        self.assert_(admin._location,
            "admin should be returned with _location")

        self.assertEquals(admin.to_dict(), test_admin.to_dict())

        admin_ids = [x.source.id for x in admins];
        self.assert_(admin.id in admin_ids,
            "admin test user should exist in group admin memberships")

    def testComments(self):
        """ Asset.comments -> /assets/xid/comments.json """

        if 'asset_comments' not in self.testdata:
            raise nose.SkipTest('cannot testComments without asset_comments in test data')

        self.member_credentials()

        loc = typepad.ListOf(typepad.Comment)
        test_comments = loc.from_dict(self.testdata['asset_comments'])
        num = len(test_comments)

        self.assert_(num >= 1,
            "test data asset comments should be non-empty")
        self.assert_(num <= 50,
            "test data asset comments should not exceed 50")

        test_asset = test_comments[0].in_reply_to

        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(test_asset.url_id)
        comments = asset.comments.filter(max_results=num)
        comments1 = asset.comments.filter(max_results=5, start_index=1)
        if num > 5:
            comments2 = asset.comments.filter(max_results=num-5, start_index=6)
        typepad.client.complete_batch()

        # test asset was retreived okay
        self.assert_(asset, "asset request should succeed")
        self.assert_(asset._location, "retrieved asset should have a _location")

        self.assertEquals(len(comments), num,
            "number of comments retrieved should match requested size")
        if num > 5:
            self.assertEquals(len(comments1) + len(comments2), num,
                "number of comments retrieved for set 1 and set 2 should equal %d" %
                num)

        self.assertEquals(comments.total_results,
            test_comments.total_results,
            "retrieved totalResults should match totalResults in test data")
        self.assertEquals(comments1.total_results,
            test_comments.total_results,
            "subset totalResults should match totalResults in test data")
        if num > 5:
            self.assertEquals(comments2.total_results,
                test_comments.total_results,
                "subset totalResults should match totalResults in test data")

        # compare against asset reference rather than 'asset' itself, since
        # the data elements differ between these two responses
        self.assertEquals(comments.to_dict(), test_comments.to_dict())

    # TODO: (lots!)
    # - featured members
    # - post creation
    # - post deletion (by regular user, by admin)
    # - post deletion failure by non-author user
    # - test for failure of post by non-member / blocked user
    # - comment creation
    # - comment deletion (by regular user, by admin)
    # - comment deletion failure by non-commenter user
    # - favorite creation
    # - favorite deletion

if __name__ == '__main__':
    utils.log()
    unittest.main()
