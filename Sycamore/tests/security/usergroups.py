import sys, os, unittest, random, time, copy
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..'))])
import __init__

from basics import RequestBasics

from Sycamore import request, config, wikiutil, wikiacl, user
from Sycamore.Page import Page
from Sycamore.wikiacl import ACL_RIGHTS_TABLE
_did_rollback = False

def make_random_string(length, alphanum_only=True):
  import random, string
  chars = string.letters + string.digits # not everything, but good nuff for now
  rand_char_loc = random.randint(0, len(chars)-1)
  random_string = ''
  for j in xrange(0, random.randint(0, length)):
      random_string += random.choice(chars)
  return random_string


def make_impossible_pages(request, numpages, max_length):
    """
    Make a list of numpages pagenames that can't exist (aren't in the list of all pages).
    """
    import random
    all_pages = [ pagename.lower() for pagename in wikiutil.getPageList(request) ]
    impossible = []
    for i in xrange(0, numpages):
       random_string = None
       random_string_lower = None
       while random_string_lower not in all_pages and random_string is None:
          random_string = make_random_string(max_length)
          random_string_lower = random_string.lower()
       impossible.append(random_string)
    return impossible

def _create_username():
    return make_random_string(20).lower()

def _create_groupname():
    return make_random_string(20)

def _create_ip():
    return '%s.%s.%s.%s' % (random.randint(0, 255), random.randint(0,255), random.randint(0,255), random.randint(0,255))

class BasicUserGroups(RequestBasics):
    def testUserGroupAdd(self):
        """Tests the ability to add users to a user group."""
        for i in range(0, 20):
            groupname = _create_groupname()
            group = wikiacl.Group(groupname, self.request)
            for j in range(0, 5):
                username = _create_username()
                group.add(username)
                self.assertTrue(username in group)

    def testUserGroupRemove(self):
        """Tests the ability to remove users from a user group."""
        for i in range(0, 20):
            groupname = _create_groupname()
            group = wikiacl.Group(groupname, self.request)
            added_usernames = []
            for j in range(0, 10):
                username = _create_username()
                group.add(username)
                added_usernames.append(username)

            for username in added_usernames:
                group.remove(username)
                self.assertTrue(username not in group)

    def testIPsAdd(self):
        """Tests the ability to add ips."""
        group = wikiacl.Group('Banned', self.request)
        for i in range(0, 50):
            ip = _create_ip()
            group.add_ip(ip)
            self.assertTrue(ip in group.get_ips())

    def testIPsRemove(self):
        """Tests the ability to remove ips."""
        group = wikiacl.Group('Banned', self.request)
        added_ips = []
        for i in range(0, 50):
            ip = _create_ip()
            group.add_ip(ip)
            added_ips.append(ip)
        for ip in added_ips:
            group.remove_ip(ip)
            self.assertTrue(ip not in group.get_ips())

    def testGroupSave(self):
        """
        Tests saving changes to the group.
        """
        def _test_with_adding():
            groups = {}
            for i in range(0, 20):
                groupname = _create_groupname()
                group = wikiacl.Group(groupname, self.request)
                groups[groupname] = []
                for j in range(0, 5):
                    username = _create_username()
                    group.add(username)
                    groups[groupname].append(username)
                group.save()
                del group

                for groupname in groups:
                   group = wikiacl.Group(groupname, self.request)
                   for username in groups[groupname]:
                       self.assertTrue(username in group)

        def _test_with_adding_then_removing():
            groups = {}
            for i in range(0, 20):
                groupname = _create_groupname()
                group = wikiacl.Group(groupname, self.request)
                groups[groupname] = []
                for j in range(0, 5):
                    username = _create_username()
                    group.add(username)
                    groups[groupname].append(username)
                group.save()
                del group

                for groupname in groups:
                   group = wikiacl.Group(groupname, self.request)
                   for username in groups[groupname]:
                       group.remove(username)
                   group.save()

                for groupname in groups:
                   group = wikiacl.Group(groupname, self.request)
                   for username in groups[groupname]:
                       self.assertTrue(username not in group)


        _test_with_adding()
        _test_with_adding_then_removing()

        # cleanup...we can fix this by putting every test in a class derived from RequestBasics
        self.request.db.do_commit = False
        self.request.db_disconnect()
        self.request = request.RequestDummy()

    def testSetDefaultRights(self):
        """
        Tests setting the default rights for the groups.
        """
        wiki_name = self.request.config.wiki_name

        # create some groups..yay!
        for i in range(0, 2):
            groupname = _create_groupname()
            group = wikiacl.Group(groupname, self.request, fresh=True)
            for j in range(0, 5):
                username = _create_username()
                # save the user
                user.User(self.request, name=username).save(new_user=True)
                group.add(username)
            group.save()

        def _create_rights(groups):
            rights = {}
            for groupname in groups:
               if groupname in ["Admin", "All", "Known", "Banned"]:
                 continue
               rights[groupname] = (random.choice([True, False]), random.choice([True, False]), random.choice([True, False]), random.choice([True, False]))
            rights['All'] = (random.choice([True, False]), random.choice([True, False]), random.choice([True, False]), False)
            rights['Known'] = (random.choice([True, False]), random.choice([True, False]), random.choice([True, False]), False)
            rights['Banned'] = (random.choice([True, False]), random.choice([True, False]), random.choice([True, False]), False)
            rights['Admin'] = (True, True, True, True)
            return rights

        def _remove_preset_groups(rights):
            rights = copy.deepcopy(rights)
            del rights["All"] 
            del rights["Known"] 
            del rights["Admin"] 
            del rights["Banned"] 
            return rights

        def _check_page_rights(rights):
            page = Page('this page has never existed.%s' % time.time(), self.request)
            for groupname in rights.keys():
                 group = wikiacl.Group(groupname, self.request, fresh=True)
                 if not group.users():
                    continue
                 random_username_in_group = random.choice(group.users())
                 random_user = user.User(self.request, name=random_username_in_group)

                 
                 may_read_status = False
                 may_edit_status = False
                 may_delete_status = False
                 may_admin_status = False

                 
                 
                 # we need to do an OR over all of the groups the user is in
                 user_is_in_a_group = False
                 for iter_groupname in _remove_preset_groups(rights):
                    iter_group = wikiacl.Group(iter_groupname, self.request, fresh=True)
                    if random_user.name in iter_group:
                       user_is_in_a_group = True
                       may_read_status = may_read_status or rights[iter_groupname][ACL_RIGHTS_TABLE['read']]
                       may_edit_status = may_edit_status or rights[iter_groupname][ACL_RIGHTS_TABLE['edit']]
                       may_delete_status = may_delete_status or rights[iter_groupname][ACL_RIGHTS_TABLE['delete']]
                       may_admin_status = may_admin_status or rights[iter_groupname][ACL_RIGHTS_TABLE['admin']]

                 if not user_is_in_a_group:
                    # Set up the default rights for the user
                    may_read_status = rights['All'][ACL_RIGHTS_TABLE['read']] or rights['Known'][ACL_RIGHTS_TABLE['read']]
                    may_edit_status = rights['All'][ACL_RIGHTS_TABLE['edit']] or rights['Known'][ACL_RIGHTS_TABLE['edit']]
                    may_delete_status = rights['All'][ACL_RIGHTS_TABLE['delete']] or rights['Known'][ACL_RIGHTS_TABLE['delete']]
                    may_admin_status = rights['All'][ACL_RIGHTS_TABLE['admin']] or rights['Known'][ACL_RIGHTS_TABLE['admin']]

                 if random_user.name in wikiacl.Group('Banned', self.request, fresh=True):
                       may_read_status = rights['Banned'][ACL_RIGHTS_TABLE['read']]
                       may_edit_status = rights['Banned'][ACL_RIGHTS_TABLE['edit']]
                       may_delete_status = rights['Banned'][ACL_RIGHTS_TABLE['delete']]
                       may_admin_status = rights['Banned'][ACL_RIGHTS_TABLE['admin']]

                                  
                 if random_user.name in wikiacl.Group('Admin', self.request, fresh=True):
                       # admins are gods
                       may_read_status = True
                       may_edit_status = True
                       may_delete_status = True
                       may_admin_status = True

                 
                 self.assertEqual(may_read_status, random_user.may.read(page, fresh=True))
                 self.assertEqual(may_admin_status, random_user.may.admin(page, fresh=True))
                 self.assertEqual(may_edit_status, random_user.may.edit(page, fresh=True))
                 self.assertEqual(may_delete_status, random_user.may.delete(page, fresh=True))


        for i in range(0, 10):
            groups = wikiacl.AccessControlList(self.request).grouplist()
            rights = _create_rights(groups)
            self.request.config.acl_rights_default = rights
            self.request.config.set_config(self.request.config.wiki_name, self.request.config.get_dict(), self.request)
            self.assertEqual(self.request.config.acl_rights_default, rights)
            wiki_config = config.Config(self.request.config.wiki_name, self.request, fresh=True)
            self.assertEqual(wiki_config.acl_rights_default, rights)
            # test to make sure that a wiki page w/o custom rights has these default rights.
            _check_page_rights(rights)

        # cleanup...we can fix this by putting every test in a class derived from RequestBasics
        self.request.db.do_commit = False
        self.request.db_disconnect()
        self.request = request.RequestDummy()

        
if __name__ == "__main__":
    unittest.main()
