from django.shortcuts import render
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Post, Comment, Tag
from .serializers import PostSerializer, CommentSerializer, PostListSerializer, TagSerializer
from .permissions import IsOwnerReadOnly
from rest_framework.exceptions import PermissionDenied

from django.shortcuts import get_object_or_404
# Create your views here.
class PostViewSet(viewsets.ModelViewSet):
    queryset= Post.objects.all()
    
    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        return PostSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        post = serializer.instance
        self.handle_tags(post)

        return Response(serializer.data)
    
    def perform_update(self, serializer):
        post = serializer.save()
        post.tag.clear()
        self.handle_tags(post)

    def handle_tags(self, post):
        tags= [word[1:] for word in post.content.split(' ') if word.startswith('#')]
        for t in tags:
            tag, created=Tag.objects.get_or_create(name=t)
            post.tag.add(tag)
        post.save()

        

    def get_permissions(self):
        if self.action in ["update","destroy","partial_update"]:
            return[IsOwnerReadOnly()]
        
        elif self.action in ["create","like"]:
            return[IsAuthenticated()]
        return []

    @action(methods=["GET"], detail=True)
    def likes(self, request, pk=None):
        like_post = self.get_object()
        user = request.user

        if user in like_post.like_user.all():
            like_post.like_user.remove(user)
            like_post.like_cnt -= 1
        else:
            like_post.like_user.add(user)
            like_post.like_cnt += 1
        like_post.save(update_fields=["likes"])
        return Response()
    



    @action(methods=["GET"], detail=False)
    def top_liked(self, request):
        top_posts = self.get_queryset().order_by('-likes')[:3]
        serializer = PostListSerializer(top_posts, many=True)
        return Response(serializer.data)
    

class CommentViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin):
    queryset=Comment.objects.all()
    serializer_class= CommentSerializer
    
    def get_permissions(self):
        if self.action in ["update", "destroy", "partial_update"]:
            return [IsOwnerReadOnly()]
        return []

class PostCommentViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin):
    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "destroy", "partial_update"]:
            return [IsOwnerReadOnly()]
        return []

    def get_queryset(self):
        post = self.kwargs.get("post_id")
        queryset = Comment.objects.filter(post_id=post)
        return queryset
    
    
    def create(self, request,post_id=None):
        post=get_object_or_404(Post, id= post_id)
        serializer=self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post)
        return Response(serializer.data)
    

class TagViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    queryset = Tag.objects.all()
    serializer_class=TagSerializer
    lookup_field="name"
    lookup_url_kwarg="tag_name"

    def retrieve(self, request, *args, **kwargs):
        tag_name= kwargs.get("tag_name")
        tag = get_object_or_404(Tag, name=tag_name)
        posts= Post.objects.filter(tag=tag)
        serializer= PostSerializer(posts, many=True)
        return Response(serializer.data)
    

@api_view(['GET', 'POST'])
def comment_read_create(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'GET':
        comments = Comment.objects.filter(post=post)
        serializer = CommentSerializer(comments, many=True)
        return Response(data=serializer.data)
    elif request.method == 'POST':
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(post=post)
        return Response(serializer.data)
    
@api_view(['GET'])
def find_tag(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name)
    if request.method == 'GET':
        post = Post.objects.filter(tag__in=[tag])
        serializer = PostSerializer(post, many=True)
        return Response(data=serializer.data)



    
    

    