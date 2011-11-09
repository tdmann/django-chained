"""
Chain core classes - allows cascading selection and editing of
models linked by foreign keys.
"""

import re
from django.db.models import Model, ForeignKey
from django.db.models.query import QuerySet
from django.db.models.fields.related import ManyToManyField
from django.db.models.signals import post_save, post_delete

def _capwords_to_underscore(name):
    return re.sub(r'(?<=[a-z])[A-Z]', r"_\g<0>", name).lower()

def _get_related_fields(model, target_model):
    # Return all fields related to the provided model

    # get all fields on this link's
    # model
    fields = model._meta.local_fields + \
             model._meta.local_many_to_many
    
    # filter those for ones with a relation
    relation_fields = [field for field in fields if hasattr(field, "related") and field.related != None and field.related.parent_model == target_model]

    return relation_fields

class AliasDescriptor(object):
    """
    Implements the descriptor protocol to allow an object
    to provide an alias for a target object's methods.
    """

    def __init__(self, target, member, attached):
        """
        Creates an alias for the specified member of the
        target object.

        The target can be a function which will be called
        when resolving the alias - the function should 
        return an appropriate object.

        member is the name of the member as a string.
        """
        self.target = target
        self.member = member
        self.attached = attached

    def _get_target(self):
        if hasattr(self.target, "__call__"):
            return self.target()
        else:
            return self.target
    
    def __call__(self, *args, **kwargs):
        target = self._get_target()
        return getattr(target, self.member)(*args, **kwargs)

    def __get__(self, instance, owner):
        target = self._get_target()
        return getattr(target, self.member)
    
    def __set__(self, instance, value):
        target = self._get_target()
        setattr(target, self.member, value)

    def __delete__(self, instance):
        target = self._get_target()
        delattr(target, self.member)
            

class BaseChainLink(object):
    """
    A single link in a chain. 

    Exposes all fields of an object instance, and provides methods to 
    save, create, delete, and select objects which exist on the tied 
    model.
    """
    def __init__(self, chain=None):
        """
        Create a ChainLink for the specified chain.
        """
        self._chain = chain
        self.instance = None

        self._parent_link = None
        self._parent_relation = None
        self._parent_relation_is_m2m = False

        self._child_link = None
        self._child_relation = None

        post_save.connect(self._post_save_received, sender=self._meta.model)
        post_delete.connect(self._post_delete_received, 
                sender=self._meta.model)

        self._create_accessors()

    def _create_accessors(self):
        # add accessors for members of this 
        # ChainLink's instance
        for member in dir(self._meta.model()):
            attr_name = name = member
            if hasattr(self, attr_name):
                attr_name = "instance_%s" % name
            setattr(self, attr_name, 
                    AliasDescriptor(lambda: self.instance, name, self))

    def _link_child(self, child_link, field=None):
        # links a child to this ChainLink - a specific
        # field can be specified to link on in the case
        # that there are multiple fields connecting the
        # two

        if not field:
            # if no field was passed, find the first field
            # that relates this link's model to the 
            # child link's model

            # these aspects should probably be refactored out
            # such that fields are determined at initialization
            # time rather than as a link is being made
            fields = _get_related_fields(self._meta.model, 
                    child_link._meta.model) + \
                    _get_related_fields(child_link._meta.model, 
                            self._meta.model)

            field = fields[0]
        
        # figure out which direction we're coming from -
        # many-to-many relations can exist on either model
        if field.related.parent_model == self._meta.model:
            self._child_relation = field.related.get_accessor_name()
            child_link._parent_relation = field.name
        elif field.related.model == self._meta.model:
            self._child_relation = field.name
            child_link._parent_relation = \
                    field.related.get_accessor_name()
        else:
            message  = "The provided field %s does not"
            message += " specifiy a relation between a"
            message += " %s and a %s."
            message = message % (field, self._meta.model, 
                    child_link._meta.model)
            raise AttributeError(message)
        
        child_link._parent_relation_is_m2m = isinstance(field,
                ManyToManyField)

        self._child_link = child_link
        child_link._parent_link = self

    def _did_select(self):
        # a method for adding special processing to ChainLinks
        # upon selection
        pass

    def select_via_get(self, **kwargs):
        """
        Performs a 'get' to select this link's instance.
        """
        self.select(self._meta.model.objects.get(**kwargs))

    def select_first(self):
        """
        Selects the first object on this link, cascading
        appropriately.
        """
        first = self.first()
        self.select(first)

    def select_last(self):
        """
        Selects the last object on this link.
        """
        last = self.last()
        self.select(last)
    
    def select_next_sibling(self):
        """
        Selects the next sibling of the current instance
        """
        self.select(self.next_sibling())
    
    def select_previous_sibling(self):
        """
        Selects the previous sibling of the current instance
        """
        self.select(self.previous_sibling())

    def select(self, model_instance):
        """
        Selects the provided model instance on this link.

        If this is a new object, set it's parent field appropriately.
        """

        # ensure that if we're setting the instance
        # to a new object, that there is an object selected
        # on the chainlink above
        # (What about setting a new object on a new object parent?)
        if not model_instance.pk and \
                self._parent_link and \
                not self._parent_link.instance:
            message  = 'Cannot create a new %s child on unselected %s '
            message += 'ChainLink'
            message  = message % (self._meta.model,
                    self._parent_link._meta.model)
            raise ValueError(message)
        
        self.instance = model_instance
        if self._parent_link:
            self._parent_link._cascade_from_child()
        if self._child_link:
            self._child_link._cascade_from_parent()
        self._did_select()

    def selected(self):
        """
        Returns true if this object has an instance set.
        """
        return self.instance != None

    def link_set(self):
        """
        Gets a queryset containing all the currently selected parents
        children or all top level objects, ordered by default ordering,
        or the public key if none is specified
        """
        if self._parent_link:
            qs = self._parent_link.children
        else:
            qs = self._meta.model.objects.all()
        if not self._meta.model._meta.ordering:
            qs.order_by("pk")
        return qs
        
    def index(self):
        """
        Returns the index of the current instance in relation to
        its parent - or if it has no parent, in relation to all
        objects of this ChainLink's model
        """
        qs = self.link_set()

        for i, obj in enumerate(qs):
            if obj == self.instance
                return i
        
        if self._parent_link
            message = "%s instance %s not found in chained children of %s"
            message = message % (self._meta.model, self.instance, 
                self._parent_link._meta.model)
        else:
            message = "%s instance %s not found - no index."
            message = message % (self._meta.model, self.instance)
        raise KeyError(message)

    def next_sibling(self, **kwargs):
        """
        Finds the next sibling of the currently selected instance.
        """

        assert(self.selected(), 
                "Cannot find next sibling on unselected ChainLink for %s" % \
                (self._meta.model))

        qs = self.link_set()
        count = qs.count()
        if not count:
            return None

        index = self.index()
        if index + 1 >= count:
            return None
        else:
            return qs[index+1]

    def previous_sibling(self, **kwargs):
        """
        Finds the next sibling of the currently selected instance.
        """
        assert(self.selected(), 
                "Cannot find previous sibling on unselected ChainLink" + \
                "for %s" % (self._meta.model))

        qs = self.link_set()
        count = qs.count()
        if not count:
            return None

        index = self.index()
        if index - 1 < 0:
            return None
        else:
            return qs[index-1]
    
    def first(self, **kwargs):
        """
        Finds the first sibling of the currently selected instance.
        """
        qs = self.link_set()
        count = qs.count()
        if not count:
            return None
        
        return qs[0]

    def last(self, **kwargs):
        """
        Finds the last sibling of the currently selected instance.
        """
        qs = self.link_set()
        count = qs.count()
        if not count:
            return None
        
        return qs[-1]

    def children(self):
        """
        Returns all children of this ChainLink's instance as a QuerySet
        """
        assert(self.selected(), 
                "Cannot get children on unselected ChainLink" + \
                "for %s" % (self._meta.model))

        if not self._child_link:
            return self._meta.model.objects.none()
        
        return getattr(self.instance, self._child_relation).all()

    # implement the descriptor protocol to allow for
    # funky nice setting of links
    def __get__(self, instance, owner):
        return self
    
    def __set__(self, instance, value):
        # Sets a chain link to point to the provided
        # model instance.
        if issubclass(value.__class__, Model):
            self.select(value)
        elif issubclass(value.__class__, ChainLink):
            message = 'Cannot replace chain links'
            raise ValueError(message)
        else:
            message = 'Cannot set link to %s instance' % \
                      (value.__class__.__name__)
            raise ValueError(message)
    
    def __delete__(self, instance):
        raise AttributeError('Cannot delete a ChainLink')

    def _get_first_parent(self):
        # If an instance is selected on this link, return the first
        # related object of the parent_link's type.
        if not self.instance:
            return None
        
        result = getattr(self.instance, self.parent_relation)

        if isinstance(result, QuerySet):
            # if this is a queryset, return the first object
            if len(result) > 0:
                return result[0]
            else:
                return None
        else:
            # otherwise it should be an object
            return result

    def _get_children(self):
        # If an instance is selected on this link, return a queryset
        # of all related child objects
        if not self.instance:
            return None
        
        return getattr(self.instance, self._child_relation)

    def _cascade_from_child(self):
        # select the appropriate instance by examining
        # the child link's instance

        # if the child hasn't been saved at all, everything
        # should remain as is so that an object can be added
        if self._child_link.instance.pk == None:
            return

        # if the child instance is already child of this link's parent
        # instance, we don't cascade up the chain.
        children = self._get_children()
        if self._child_link.instance == None or \
           (children and children.exists(self._child_link.instance)):
            return
        
        # otherwise, select the first parent of the child link's instance
        # and update the next parent link
        self.instance = self._child_link._get_first_parent()
        if self._parent_link:
            self._parent_link._cascade_from_child()
    
    def _cascade_from_parent(self):
        # select the appropriate child by examining
        # the parent link's instance

        if (self._parent_link.instance == None or 
                self._parent_link.instance.pk == None):
            self.instance = None
        else:
            children = self._parent_link._get_children()
            if children.count() > 0:
                # if children exist on the parent, select the first
                self.instance = children[0]
            else:
                # automatically create and select (but don't save)
                # a new instance of this link's model if
                # auto_create_defaults is set
                if self._chain.auto_create_defaults:
                    self.instance = model()
                else:
                    self.instance = None
        
        # update this link's child link
        if self._child_link:
            self._child_link._cascade_from_parent()
    
    def _post_save_received(self, sender, instance, created, **kwargs):
        # when an object in this chain gets saved, make sure
        # its parent is set if it was just created, or
        # cascade from this object to select correct objects
        # in the case of a move
        if not instance == self.instance:
            return

        # set parents on newly saved instances
        if created and self._parent_link:
            # make sure we don't get stuck in a signal loop
            post_save.disconnect(self._post_save_received, self._meta.model)

            # on m2m relations we need to add parents, not set them
            if self._parent_relation_is_m2m:
                related_set = getattr(self.instance, self._parent_relation)
                related_set.add(self._parent_link.instance)
            else:
                setattr(self.instance, self._parent_relation, 
                    self._parent_link.instance)

            # save changes and reset the signal listener
            self.instance.save()
            post_save.connect(self._post_save_received, 
                    sender=self._meta.model)
        
        # allow moving by updating the chain after a save - we only
        # do this when an object wasn't created to allow a person
        # to save multiple new objects on different levels of the chain.
        if not created:
            if self._parent_link:
                self._parent_link._cascade_from_child()
            else:
                self._child_link.cascade_from_parent()

    def _pre_delete_received(self, sender, instance, **kwargs):
        # when an object is deleted, we want to make sure
        # we shift selection to a different object
        if not instance == self.instance:
            return
        self.select_previous()

class ChainLinkOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)

class ChainLinkMetaclass(type):
    """
    Allows a chain link to reflect the selected model instance.
    """
    def __new__(cls, name, bases, attrs):
        new_class = super(ChainLinkMetaclass, cls).__new__(cls, name, bases, 
                attrs)
        # make sure we aren't defining ChainLink itself
        try:
            parents = [b for b in bases if issubclass(b, ChainLink)]
        except NameError:
            return new_class
        options = new_class._meta = ChainLinkOptions(getattr(new_class, 
                'Meta', None))
        return new_class

class ModelFormChainLinkOptions(ChainLinkOptions):
    def __init__(self, options=None):
        self.form_class = getattr(options, 'modelform_class', None)
        super(ModelFormChainLinkOptions, self).__init__(options)
    
class ModelFormChainLinkMetaclass(type):
    def __new__(cls, name, bases, attrs):
        new_class = super(ModelFormChainLinkMetaclass, cls).__new__(cls, 
                name, bases, attrs)
        # make sure we aren't defining ModelFormChainLink itself
        try:
            parents = [b for b in bases if issubclass(b, ModelFormChainLink)]
        except NameError:
            return new_class
        options = new_class._meta = ModelFormChainLinkOptions(
                getattr(new_class,'Meta', None))
        return new_class

class ChainLink(BaseChainLink):
    __metaclass__ = ChainLinkMetaclass

class ModelFormChainLink(BaseChainLink):
    __metaclass__ = ModelFormChainLinkMetaclass

    def __init__(self, chain):
        """
        Allows a chain to associate model forms with 
        each level of this Chain.
        """
        self._form = None
    
    def _did_select(self):
        if not self.instance:
            self._form = None
        else:
            self._form = self._meta.model_form_class(instance=self.instance)

    def save_form_data(self, data=None, files=None, commit=True):
        """
        Saves form data to the currently selected instance, or,
        if no instance is selected, saves the form data to a new
        instance and sets the appropriate parent.
        """
        form = self._meta.model_form_class(data=data, files=files, 
                instance=self.instance)
        if self.instance:
            self.instance = form.save(commit=commit)
        else:
            self.instance = form.save(commit=commit)

class BaseChain(object):
    """
    Base class for a chain.

    Chains a set of models together to allow for cascading selection of
    models linked by foreign keys. Creates and manages the sub
    ChainLinks involved.
    """
    def __init__(self, auto_create_defaults=False):
        """
        Initializes this chain.

        auto_create_defaults - When True, the first instance of an empty
                               selection in a chain will be replaced by
                               a new instance of that chains model, which
                               can then be modified and saved. 
        """
        self.auto_create_defaults = auto_create_defaults

        self._links = {}
        self._links_list = []

        for key, link_class in self._meta.links:
            new_link = link_class(chain=self)
            self._links.update({key: new_link})
        
            # link to the last link
            if len(self._links_list) > 0:
                last_link = self._links_list[-1]
                self._connect_links(last_link, new_link)
        
            # add the new link to the indexed list
            self._links_list.append(new_link)

            # add a property to access this link
            setattr(self.__class__, key, new_link)
        
        self.select_first()

    def select_first(self):
        """
        Selects the first object available for each link in the chain.
        """
        if len(self._links_list) > 0:
            self._links_list[0].select_first()
    
    def _connect_links(self, parent, child):
        # Connect the parent and child links
        parent._link_child(child)


# These Chain Metaclasses can probably be refactored to better fit
# DRY principles.
class ChainOptions(object):
    def __init__(self, options=None):
        self.models = getattr(options, 'models', None)
        
class ChainMetaclass(type):
    def __new__(cls, name, bases, attrs):
        new_class = super(ChainMetaclass, cls).__new__(cls, name, 
                bases, attrs)

        # check if we're building Chain
        try:
            parents = [b for b in bases if issubclass(Chain, b)]
        except NameError:
            return new_class

        # build the class based off options
        options = new_class._meta = ChainOptions(getattr(new_class, 'Meta', 
                None))
        new_class._meta.links = []

        # make accessors for each
        if options.models:
            for model in options.models:
                key = None
                if isinstance(model, tuple) and len(model) == 2:
                    # if we're looking at a tuple, split it and  
                    # take the first entry as the key for this model
                    key, model = model.split()
                elif issubclass(model, Model):
                    # otherwise generate the key
                    key = _capwords_to_underscore(model.__name__)

                # create an appropriate link class
                link_class = type('ChainLink_%s' % key, 
                        (ChainLink,), 
                        dict(Meta=type('Meta', (object,), 
                                dict(model=model))))

                # add the link to the meta class
                new_class._meta.links.append((key, link_class))

        return new_class

class ModelFormChainOptions(ChainOptions):
    def __init__(self, options=None):
        self.model_form_classes = getattr(options, 
                'model_form_classes', None)
        super(ModelFormChainOptions, self).__init__(options)

class ModelFormChainMetaclass(type):
    def __new__(cls, name, bases, attrs):
        new_class = super(ModelFormChainMetaclass, cls).__new__(cls, name,
                bases, attrs)
        
        # check if we're building ModelFormChain
        try:
            parents = [b for b in bases if issubclass(ModelFormChain, b)]
        except NameError:
            return new_class

        # build the class based off options
        options = new_class._meta = ModelFormChainOptions(getattr(new_class, 'Meta', 
                None))
        new_class._meta.links = []

        # make accessors for each
        if options.models:
            for model, model_form_class in zip(options.models, 
                    options.model_form_classes):
                key = None
                if isinstance(model, tuple) and len(model) == 2:
                    # if we're looking at a tuple, split it and  
                    # take the first entry as the key for this model
                    key, model = model.split()
                elif issubclass(model, Model):
                    # otherwise generate the key
                    key = _capwords_to_underscore(model.__name__)

                chain_link_meta = type('Meta', (object,), dict(model=model, 
                        model_form_class=model_form_class))

                chain_link_dict = dict(Meta=chain_link_meta)

                # create an appropriate link class
                link_class = type('ChainLink_%s' % key, 
                        (ModelFormChainLink,), 
                        chain_link_dict)

                # add the link to the meta class
                new_class._meta.links.append((key, link_class))
        return new_class

class Chain(BaseChain):
    __metaclass__ = ChainMetaclass

class ModelFormChain(BaseChain):
    __metaclass__ = ModelFormChainMetaclass
