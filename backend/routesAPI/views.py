import us
import os
import math
import requests
import pandas as pd
import reverse_geocoder as rg
from django.conf import settings
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

        if route_response['status'] != 'OK':
            return Response({'error': 'Invalid Coordinates'}, status=status.HTTP_400_BAD_REQUEST)

        distance_meters = route_response['routes'][0]['legs'][0]['distance']['value']
        distance_miles = float(f'{(distance_meters / 1609.34):.2f}')
        print('total_distance ==> ', distance_miles)

        MAX_RANGE = 500 # in miles
        df = pd.read_csv('fuel-prices.csv')
        milestones = []
        legs = route_response['routes'][0]['legs']
        interval_distance = 500 * 1609.34
        cumulative_distance = 0
        next_milestone = interval_distance
        target_states = []
        cities = ""
        gallons_needed = distance_miles / 10
        avg_fuel_cost = df['Retail Price'].mean()
        total_fuel_cost = gallons_needed * avg_fuel_cost

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
            file_path = os.path.join(settings.MEDIA_ROOT, "static_map.png")
            with open(file_path, "wb") as f:
                f.write(static_map_response.content)

            # Generate the image URL
            image_url = request.build_absolute_uri(settings.MEDIA_URL + "static_map.png")

            # Return JSON response with the image URL
            if distance_miles <= MAX_RANGE:
                return Response({
                    "image_url": image_url,
                    "trip_data": {
                        "distance_miles": distance_miles,
                        "fuel_stops": "None",
                        "total_fuel_cost": f'${total_fuel_cost:.2f}',
                    }})

        else:
            return Response(f"Error fetching static map: {static_map_response.status_code}", status=status.HTTP_417_EXPECTATION_FAILED)

        for leg in legs:
            for step in leg['steps']:
                step_distance = step['distance']['value']
                cumulative_distance += step_distance
                
                # Check if we've reached or passed the next milestone
                while cumulative_distance >= next_milestone:
                    lat = step['end_location']['lat']
                    lng = step['end_location']['lng']
                    milestones.append([lat, lng])

                    next_milestone += interval_distance
        
        for coord in milestones:
            result = rg.search(coord)
            target_states.append(result[0]['admin1'])

        # Initialize an empty array to store the results
        fuel_stops = []

        # Loop through each state
        for state in target_states:
            # Filter the rows for that state
            s = us.states.lookup(state)
            s = s.abbr
            df_state = df[df['State'] == s]                
            # Find the row with the lowest retail price in that state
            lowest_price_row = df_state.loc[df_state['Retail Price'].idxmin()]
            
            # Add relevant info to the fuel_stops array
            fuel_stops.append({
                'State': s,
                'City': lowest_price_row['City'],
                'Truckstop Name': lowest_price_row['Truckstop Name'],
                'Address': lowest_price_row['Address'],
                'Retail Price': lowest_price_row['Retail Price']
            })

        for stop in fuel_stops:
            cities += stop['City'].strip() + ', '
            cities += stop['State'].strip() + ' | Fuel price: $'
            cities += str(stop['Retail Price'])
            cities += '+'

        waypoints = [wp for wp in cities.split('+') if wp]

        return Response({
            "image_url": image_url,
            "trip_data": {
                "distance_miles": distance_miles,
                "fuel_stops": waypoints,
                "total_fuel_cost": f'${total_fuel_cost:.2f}',
            }})