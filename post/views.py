from django.shortcuts import render
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Post, Comment, Tag
from .serializers import PostSerializer, CommentSerializer, PostListSerializer, TagSerializer
from .permissions import IsOwnerReadOnly,IsAuthenticatedOrReadOnly
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
        
        elif self.action in ["create"]:
            return[IsAuthenticated()]
        return []

    @action(methods=["GET"], detail=True, permission_classes=[IsAuthenticated])
    def likes(self, request, pk=None):
        likes_post = self.get_object()
        user = request.user

        if likes_post.likes.filter(id=user.id).exists():
            likes_post.likes.remove(user)
            likes_post.like_cnt -= 1
            liked = False
        else:
            likes_post.likes.add(user)
            likes_post.like_cnt += 1
            liked = True

        likes_post.save(update_fields = ["likes"])
        return Response({"liked": liked, "likes": likes_post.likes})
    



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
    queryset= Comment.objects.all()
    serializer_class=CommentSerializer
    permission_classes=[IsAuthenticated]

    def list(self, request, post_id=None):
        post= get_object_or_404(Post, id=post_id)
        queryset= self.filter_queryset(self.get_queryset().filter(post=post))
        serializer=self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
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



    
    

    