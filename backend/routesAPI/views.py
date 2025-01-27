from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response

class   RoutesView(APIView):
    def post(self, request):
        self.start_location = request.data.get('start_location')
        self.finish_location = request.data.get('finish_location')

        print('start: ', self.start_location)
        print('finish: ', self.finish_location)

        return Response({'start': self.start_location, 'finish': self.finish_location})