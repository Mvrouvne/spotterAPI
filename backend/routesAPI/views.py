import requests
from rest_framework import status
from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response

class   RoutesView(APIView):
    def post(self, request):
        start_location = request.data.get('start_location')
        finish_location = request.data.get('finish_location')

        if not 'Authorization' in request.headers:
            return Response({'error': 'Authorization key required'}, status=status.HTTP_403_FORBIDDEN)

        KEY = request.headers['Authorization']

        if not start_location or not finish_location:
            return Response({'error': 'Both coordinates should be provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        API_URL = 'https://maps.googleapis.com/maps/api/directions/json'

        route_details = requests.get(
            API_URL,
            params={
                    'origin': start_location,
                    'destination': finish_location,
                    'mode': 'driving',
                    'key': KEY,
                }
        )

        route_response = route_details.json()
        # print('route_response ==> ', response)

        if route_response['status'] != 'OK':
            return Response({'error': 'Invalid Coordinates'}, status=status.HTTP_400_BAD_REQUEST)

        distance_meters = route_response['routes'][0]['legs'][0]['distance']['value']
        distance_miles = float(f'{(distance_meters / 1609.34):.2f}')
        print('total_distance ==> ', distance_miles)

        MAX_RANGE = 500 # in miles

        if distance_miles < MAX_RANGE:
            polyline = route_response['routes'][0]['overview_polyline']['points']
            static_map_url = 'https://maps.googleapis.com/maps/api/staticmap'
            static_map_response = requests.get(
                static_map_url,
                params = {
                    "size": "600x400",
                    "path": f"enc:{polyline}",
                    "markers": f"color:blue|{start_location}",
                    "markers": f"color:red|{finish_location}",
                    "key": KEY
                })
            
            # Save the image
            if static_map_response.status_code == 200:
                 return HttpResponse(static_map_response.content, content_type="image/png")
            else:
                print(f"Error fetching static map: {static_map_response.status_code}")
        
        ## import fuel fiel using pandas

        return Response({'response': route_response})